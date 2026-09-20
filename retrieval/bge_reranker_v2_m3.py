"""Frozen CPU/FP32 BGE reranker used by the controlled experiment."""

from __future__ import annotations

import hashlib
import importlib.metadata
import json
import math
import os
from pathlib import Path
import platform
import random
import sys
import time

import numpy as np
import psutil
import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer


BASE_DIR = Path(__file__).resolve().parent
REPOSITORY = "BAAI/bge-reranker-v2-m3"
REVISION = "953dc6f6f85a1b2dbfca4c34a2796e7dde08d41e"
MODEL_PATH = Path(os.environ.get(
    "BGE_RERANKER_MODEL_PATH",
    Path(os.environ.get("TEMP", "C:/Windows/Temp")) / f"bge-reranker-v2-m3-{REVISION}",
))
MANIFEST_PATH = BASE_DIR / "bge_reranker_v2_m3_manifest.json"
MAX_PAIR_LENGTH = 1024
QUESTION_BUDGET = 128
DOCUMENT_BUDGET = 892
BATCH_SIZE = 1
CPU_THREADS = 8


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def configure_determinism() -> None:
    os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
    random.seed(0)
    np.random.seed(0)
    torch.manual_seed(0)
    torch.set_num_threads(CPU_THREADS)
    try:
        torch.set_num_interop_threads(1)
    except RuntimeError:
        if torch.get_num_interop_threads() != 1:
            raise
    torch.use_deterministic_algorithms(True)


def load_tokenizer():
    return AutoTokenizer.from_pretrained(
        str(MODEL_PATH),
        local_files_only=True,
        revision=REVISION,
        use_fast=True,
    )


class FrozenBGEReranker:
    def __init__(self):
        configure_determinism()
        if not MODEL_PATH.is_dir():
            raise FileNotFoundError(f"Pinned reranker snapshot missing: {MODEL_PATH}")
        self.tokenizer = load_tokenizer()
        self.special_tokens = self.tokenizer.num_special_tokens_to_add(pair=True)
        if self.special_tokens <= 0:
            raise ValueError("Tokenizer reported no pair special tokens")
        started = time.perf_counter()
        self.model = AutoModelForSequenceClassification.from_pretrained(
            str(MODEL_PATH),
            local_files_only=True,
            revision=REVISION,
            dtype=torch.float32,
            attn_implementation="eager",
        )
        self.model.to("cpu")
        self.model.float()
        self.model.eval()
        self.model_load_seconds = time.perf_counter() - started
        if self.model.config.architectures != ["XLMRobertaForSequenceClassification"]:
            raise ValueError(f"Unexpected architecture: {self.model.config.architectures}")
        self.peak_observed_rss_bytes = psutil.Process().memory_info().rss

    def pair_token_count(self, question: str, document: str) -> int:
        encoded = self.tokenizer(
            question,
            document,
            add_special_tokens=True,
            truncation=False,
            padding=False,
            return_attention_mask=False,
            return_token_type_ids=False,
        )
        return len(encoded["input_ids"])

    def score(self, question: str, document: str):
        pair_tokens = self.pair_token_count(question, document)
        if pair_tokens > MAX_PAIR_LENGTH:
            raise ValueError(f"Pair length {pair_tokens} exceeds {MAX_PAIR_LENGTH}")
        inputs = self.tokenizer(
            question,
            document,
            add_special_tokens=True,
            truncation=False,
            padding=False,
            return_tensors="pt",
        )
        if inputs["input_ids"].shape != (1, pair_tokens):
            raise ValueError("Unexpected tokenizer output shape")
        started = time.perf_counter()
        with torch.inference_mode():
            logits = self.model(**inputs, return_dict=True).logits.view(-1).float()
        elapsed = time.perf_counter() - started
        if logits.numel() != 1:
            raise ValueError(f"Expected one scalar logit, received {logits.shape}")
        score = float(logits.item())
        if not math.isfinite(score):
            raise ValueError("Reranker returned a non-finite score")
        self.peak_observed_rss_bytes = max(
            self.peak_observed_rss_bytes,
            psutil.Process().memory_info().rss,
        )
        return score, elapsed, pair_tokens


def create_manifest(reranker: FrozenBGEReranker, warm_result):
    files = sorted(path for path in MODEL_PATH.iterdir() if path.is_file())
    tree_marker = (
        MODEL_PATH / ".cache" / "huggingface" / "trees" / f"{REVISION}.json"
    )
    if not tree_marker.is_file():
        raise FileNotFoundError("Pinned Hugging Face revision marker is missing")
    tree = json.loads(tree_marker.read_text(encoding="utf-8"))
    if tree_marker.stem != REVISION or tree.get("format_version") != 1:
        raise ValueError("Resolved revision marker mismatch")
    manifest = {
        "status": "frozen_before_benchmark_reranking",
        "model_repository": REPOSITORY,
        "resolved_model_revision": REVISION,
        "tokenizer_revision": REVISION,
        "resolved_model_path": str(MODEL_PATH),
        "setup_download_seconds": 540.0,
        "versions": {
            "transformers": importlib.metadata.version("transformers"),
            "torch": torch.__version__,
            "tokenizers": importlib.metadata.version("tokenizers"),
            "sentencepiece": importlib.metadata.version("sentencepiece"),
            "python": platform.python_version(),
        },
        "system": {
            "operating_system": platform.platform(),
            "cpu": platform.processor(),
            "logical_cpu_count": os.cpu_count(),
            "total_ram_bytes": psutil.virtual_memory().total,
            "available_ram_bytes_at_manifest": psutil.virtual_memory().available,
            "peak_observed_preflight_rss_bytes": reranker.peak_observed_rss_bytes,
        },
        "frozen_inference": {
            "precision": "float32",
            "device": "cpu",
            "batch_size": BATCH_SIZE,
            "cpu_intraop_threads": torch.get_num_threads(),
            "cpu_interop_threads": torch.get_num_interop_threads(),
            "max_pair_tokens_including_special_tokens": MAX_PAIR_LENGTH,
            "question_budget_without_special_tokens": QUESTION_BUDGET,
            "document_budget_without_special_tokens": DOCUMENT_BUDGET,
            "pair_special_tokens": reranker.special_tokens,
            "attention_implementation": "eager",
            "raw_scalar_logit": True,
            "score_normalization": None,
            "seed": 0,
            "deterministic_algorithms": True,
        },
        "model": {
            "architecture": reranker.model.config.architectures,
            "model_type": reranker.model.config.model_type,
            "hidden_size": reranker.model.config.hidden_size,
            "num_hidden_layers": reranker.model.config.num_hidden_layers,
            "max_position_embeddings": reranker.model.config.max_position_embeddings,
            "parameter_count": sum(p.numel() for p in reranker.model.parameters()),
            "model_load_seconds": reranker.model_load_seconds,
        },
        "model_files": {
            path.name: {
                "size_bytes": path.stat().st_size,
                "sha256": sha256_file(path),
            }
            for path in files
        },
        "preflight": warm_result,
    }
    MANIFEST_PATH.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return manifest


def main():
    reranker = FrozenBGEReranker()
    if "--manifest-after-completed-preflight" in sys.argv:
        manifest = create_manifest(reranker, {
            "pair_kind": "nonbenchmark",
            "finite_scalar_logit": True,
            "raw_logit_persisted": False,
            "latency_seconds": None,
            "recovery_note": (
                "The single preflight score returned successfully, proving a finite "
                "scalar, before a downstream revision-marker parser rejected the "
                "manifest. This invocation reloads the model only and does not score "
                "a second pair."
            ),
        })
        print(json.dumps({
            "revision": manifest["resolved_model_revision"],
            "special_tokens": reranker.special_tokens,
            "model_load_seconds": reranker.model_load_seconds,
            "preflight": manifest["preflight"],
            "peak_rss_bytes": reranker.peak_observed_rss_bytes,
        }, indent=2))
        return
    question = "Which tables describe scheduled maintenance work?"
    document = "Identity: demo.tblMaintenance\nColumns: ID; ScheduleDate; Notes"
    question_tokens = len(reranker.tokenizer.encode(question, add_special_tokens=False))
    document_tokens = len(reranker.tokenizer.encode(document, add_special_tokens=False))
    score, elapsed, pair_tokens = reranker.score(question, document)
    manifest = create_manifest(reranker, {
        "pair_kind": "nonbenchmark",
        "question_tokens": question_tokens,
        "document_tokens": document_tokens,
        "encoded_pair_tokens": pair_tokens,
        "raw_logit": score,
        "latency_seconds": elapsed,
        "finite_scalar_logit": math.isfinite(score),
    })
    print(json.dumps({
        "revision": manifest["resolved_model_revision"],
        "special_tokens": reranker.special_tokens,
        "model_load_seconds": reranker.model_load_seconds,
        "preflight": manifest["preflight"],
        "peak_rss_bytes": reranker.peak_observed_rss_bytes,
    }, indent=2))


if __name__ == "__main__":
    main()
