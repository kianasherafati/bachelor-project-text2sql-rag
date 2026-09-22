"""Build the frozen BGE-Business-Dense one-vector-per-table index."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import pickle
import statistics
import time

os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
os.environ.setdefault("OMP_NUM_THREADS", "8")
os.environ.setdefault("MKL_NUM_THREADS", "8")

import faiss
import numpy as np
import psutil
import torch
from FlagEmbedding import BGEM3FlagModel
from transformers import AutoTokenizer


ROOT = Path(__file__).resolve().parents[1]
RETRIEVAL = ROOT / "retrieval"
EVALUATION = ROOT / "evaluation"
REPRESENTATIONS_PATH = RETRIEVAL / "bge_reranker_table_representations.json"
REPRESENTATION_AUDIT_PATH = RETRIEVAL / "bge_reranker_representation_audit.json"
REPRESENTATION_REPORT_PATH = RETRIEVAL / "bge_reranker_representation_build_report.json"
ORIGINAL_METADATA_PATH = RETRIEVAL / "schema_metadata.pkl"
MODEL_MANIFEST_PATH = RETRIEVAL / "bge_m3_model_manifest.json"
INDEX_PATH = RETRIEVAL / "bge_business_schema.index"
METADATA_PATH = RETRIEVAL / "bge_business_schema_metadata.json"
REPORT_PATH = RETRIEVAL / "bge_business_schema_build_report.json"
PROTECTED_HASHES_PATH = EVALUATION / "bge_business_dense_protected_hashes_before.json"

EXPECTED_REPRESENTATION_SHA256 = "710fbd9fcf863aeaccbd0004eafae2fa990b183b4bc6f705375ec1da5fe10966"
MODEL_REPOSITORY = "BAAI/bge-m3"
MODEL_REVISION = "5617a9f61b028005a4858fdac845db406aefb181"
EXPECTED_TABLES = 2196
DIMENSION = 1024
MAX_TOKENS = 8192
CONTENT_ALLOWANCE = 8190
CPU_THREADS = 8

torch.set_num_threads(CPU_THREADS)
torch.set_num_interop_threads(1)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def write_json(path: Path, payload) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def protected_paths() -> list[Path]:
    relatives = [
        "retrieval/bge_reranker_table_representations.json",
        "retrieval/bge_reranker_representation_audit.json",
        "retrieval/bge_reranker_representation_build_report.json",
        "retrieval/bge_m3_schema.index",
        "retrieval/bge_m3_schema_metadata.json",
        "retrieval/bge_m3_model_manifest.json",
        "retrieval/bge_m3_retriever.py",
        "retrieval/schema.index",
        "retrieval/schema_metadata.pkl",
        "retrieval/graph_expanded_retriever.py",
        "retrieval/hybrid_retriever.py",
        "retrieval/retriever.py",
        "retrieval/erp_retrieval_benchmark.py",
        "retrieval/erp_retrieval_heldout_benchmark.py",
        "evaluation/real_world_text2sql_benchmark.py",
        "evaluation/bge_reranker_candidate_lists.json",
        "evaluation/bge_reranker_comparison_results.json",
        "retrieval/bge_reranker_v2_m3.py",
        "retrieval/bge_reranker_v2_m3_manifest.json",
        "evaluation/text2sql_gold_benchmark.py",
        "evaluation/gold_sql_definitions.py",
        "evaluation/text2sql_gold_validation.json",
        "evaluation/real_world_gold_benchmark.py",
        "evaluation/real_world_gold_validation.json",
    ]
    paths = [ROOT / relative for relative in relatives]
    missing = [str(path.relative_to(ROOT)) for path in paths if not path.is_file()]
    if missing:
        raise FileNotFoundError(f"Protected artifacts missing: {missing}")
    return paths


def hashes(paths: list[Path]) -> dict[str, str]:
    return {str(path.relative_to(ROOT)): sha256_file(path) for path in paths}


def distribution(values) -> dict:
    return {
        "minimum": min(values),
        "median": statistics.median(values),
        "mean": statistics.mean(values),
        "maximum": max(values),
    }


def load_model(model_path: Path):
    started = time.perf_counter()
    model = BGEM3FlagModel(
        str(model_path), devices="cpu", use_fp16=False, use_bf16=False,
        normalize_embeddings=True, pooling_method="cls",
        query_instruction_for_retrieval=None, batch_size=1,
        query_max_length=MAX_TOKENS, passage_max_length=MAX_TOKENS,
        return_dense=True, return_sparse=False, return_colbert_vecs=False,
        local_files_only=True,
    )
    model.model.float()
    model.model.to("cpu")
    model.model.eval()
    return model, time.perf_counter() - started


def encode_document(model, content_ids: list[int]) -> np.ndarray:
    tokenizer = model.tokenizer
    input_ids = [tokenizer.cls_token_id, *content_ids, tokenizer.sep_token_id]
    if len(input_ids) > MAX_TOKENS:
        raise RuntimeError("STOP: a compact representation requires truncation")
    inputs = {
        "input_ids": torch.tensor([input_ids], dtype=torch.long),
        "attention_mask": torch.ones((1, len(input_ids)), dtype=torch.long),
    }
    with torch.inference_mode():
        output = model.model(
            inputs, return_dense=True, return_sparse=False,
            return_colbert_vecs=False, truncate_dim=None,
        )
    vector = output["dense_vecs"].detach().cpu().numpy().astype(np.float32)[0]
    if vector.shape != (DIMENSION,) or not np.isfinite(vector).all():
        raise ValueError("Invalid BGE business document vector")
    norm = np.linalg.norm(vector)
    if norm == 0:
        raise ValueError("Zero BGE business document vector")
    return vector / norm


def main() -> None:
    overall_started = time.perf_counter()
    hash_started = time.perf_counter()
    protected = protected_paths()
    before = hashes(protected)
    hash_seconds = time.perf_counter() - hash_started
    write_json(PROTECTED_HASHES_PATH, {
        "status": "frozen_before_bge_business_model_load_or_evaluation",
        "sha256": before,
    })
    if before[str(REPRESENTATIONS_PATH.relative_to(ROOT))] != EXPECTED_REPRESENTATION_SHA256:
        raise RuntimeError("STOP: frozen representation SHA-256 mismatch")

    manifest = json.loads(MODEL_MANIFEST_PATH.read_text(encoding="utf-8"))
    if manifest["resolved_model_revision"] != MODEL_REVISION:
        raise RuntimeError("STOP: frozen BGE-M3 revision mismatch")
    frozen = manifest["frozen_encoding"]
    expected_settings = {
        "dense_only": True, "pooling": "cls", "normalize_embeddings": True,
        "precision": "float32", "device": "cpu", "batch_size": 1,
        "maximum_encoded_tokens_including_special_tokens": MAX_TOKENS,
        "query_instruction_prefix": None, "embedding_dimension": DIMENSION,
        "sparse_output": False, "colbert_output": False,
    }
    for key, expected in expected_settings.items():
        if frozen[key] != expected:
            raise RuntimeError(f"STOP: frozen BGE setting changed: {key}")
    model_path = Path(manifest["resolved_model_path"])
    tokenizer = AutoTokenizer.from_pretrained(str(model_path), local_files_only=True)
    if tokenizer.num_special_tokens_to_add(pair=False) != 2:
        raise RuntimeError("STOP: expected two BGE special tokens")

    representations = json.loads(REPRESENTATIONS_PATH.read_text(encoding="utf-8"))
    if representations["table_count"] != EXPECTED_TABLES or len(representations["tables"]) != EXPECTED_TABLES:
        raise RuntimeError("STOP: expected exactly 2,196 compact representations")
    if representations["section_budgets"] != {
        "identity": 68, "table_labels": 96, "associated_forms": 128,
        "modules": 64, "columns": 536,
    } or representations["document_budget"] != 892:
        raise RuntimeError("STOP: compact representation policy changed")
    with ORIGINAL_METADATA_PATH.open("rb") as handle:
        documents = pickle.load(handle)
    expected_order = [item["full_name"] for item in documents]
    actual_order = [item["fully_qualified_table"] for item in representations["tables"]]
    if actual_order != expected_order or len(set(actual_order)) != EXPECTED_TABLES:
        raise RuntimeError("STOP: compact representation order differs from indexed corpus")

    token_started = time.perf_counter()
    token_ids = []
    counts = []
    for item in representations["tables"]:
        ids = tokenizer.encode(item["text"], add_special_tokens=False, truncation=False)
        if len(ids) > CONTENT_ALLOWANCE:
            raise RuntimeError("STOP: compact representation exceeds BGE capacity")
        token_ids.append(ids)
        counts.append(len(ids))
    token_seconds = time.perf_counter() - token_started
    truncation_count = sum(count > CONTENT_ALLOWANCE for count in counts)
    if truncation_count:
        raise RuntimeError("STOP: BGE representation truncation required")

    model, model_load_seconds = load_model(model_path)
    process = psutil.Process()
    peak_rss = process.memory_info().rss
    vectors = np.empty((EXPECTED_TABLES, DIMENSION), dtype=np.float32)
    embedding_started = time.perf_counter()
    for index, ids in enumerate(token_ids):
        vectors[index] = encode_document(model, ids)
        peak_rss = max(peak_rss, process.memory_info().rss)
        if (index + 1) % 50 == 0 or index + 1 == EXPECTED_TABLES:
            print(f"Encoded {index + 1}/{EXPECTED_TABLES} business documents", flush=True)
    embedding_seconds = time.perf_counter() - embedding_started
    norms = np.linalg.norm(vectors, axis=1)
    if not np.isfinite(vectors).all() or not np.allclose(norms, 1.0, atol=1e-5):
        raise RuntimeError("STOP: business vectors failed finite/normalization audit")

    faiss_build_started = time.perf_counter()
    index = faiss.IndexFlatIP(DIMENSION)
    index.add(vectors)
    faiss_build_seconds = time.perf_counter() - faiss_build_started
    faiss_write_started = time.perf_counter()
    faiss.write_index(index, str(INDEX_PATH))
    faiss_write_seconds = time.perf_counter() - faiss_write_started

    mapping = [{
        "vector_id": vector_id,
        "fully_qualified_table": item["fully_qualified_table"],
        "representation_sha256": item["sha256"],
        "bge_content_tokens": counts[vector_id],
        "bge_encoded_tokens": counts[vector_id] + 2,
        "truncated": False,
    } for vector_id, item in enumerate(representations["tables"])]
    write_json(METADATA_PATH, {
        "format_version": 1,
        "experiment": "BGE-Business-Dense",
        "model_repository": MODEL_REPOSITORY,
        "model_revision": MODEL_REVISION,
        "representation_sha256": EXPECTED_REPRESENTATION_SHA256,
        "vector_dimension": DIMENSION,
        "mapping": mapping,
    })
    after = hashes(protected)
    if after != before:
        raise RuntimeError("STOP: protected artifact changed during index build")
    report = {
        "experiment": "BGE-Business-Dense",
        "representation_reused_verbatim": True,
        "representation_sha256": EXPECTED_REPRESENTATION_SHA256,
        "representation_hash_verification_seconds": hash_seconds,
        "tokenization_audit_seconds": token_seconds,
        "bge_content_token_counts": distribution(counts),
        "documents_above_8190_content_tokens": sum(count > CONTENT_ALLOWANCE for count in counts),
        "documents_requiring_truncation": truncation_count,
        "table_count": EXPECTED_TABLES,
        "order_matches_original_indexed_corpus": actual_order == expected_order,
        "model_load_seconds": model_load_seconds,
        "document_embedding_build_seconds": embedding_seconds,
        "faiss_construction_seconds": faiss_build_seconds,
        "faiss_write_seconds": faiss_write_seconds,
        "peak_process_rss_bytes": peak_rss,
        "vector_count": index.ntotal,
        "vector_dimension": index.d,
        "vectors_finite": bool(np.isfinite(vectors).all()),
        "vectors_l2_normalized": bool(np.allclose(norms, 1.0, atol=1e-5)),
        "vector_norms": distribution(norms.tolist()),
        "vector_payload_bytes": vectors.nbytes,
        "serialized_index_bytes": INDEX_PATH.stat().st_size,
        "metadata_artifact_bytes": METADATA_PATH.stat().st_size,
        "total_build_wall_seconds": time.perf_counter() - overall_started,
        "protected_hashes_unchanged": True,
        "artifacts_sha256": {
            str(INDEX_PATH.relative_to(ROOT)): sha256_file(INDEX_PATH),
            str(METADATA_PATH.relative_to(ROOT)): sha256_file(METADATA_PATH),
        },
    }
    write_json(REPORT_PATH, report)
    print(json.dumps(report, indent=2), flush=True)


if __name__ == "__main__":
    main()
