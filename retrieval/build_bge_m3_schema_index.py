"""Build the frozen one-vector-per-table BGE-M3 experimental index.

This module is intentionally separate from every frozen MiniLM implementation.
It also creates the pre-result provenance, integrity, coverage, and hypothesis
artifacts required by the controlled experiment.
"""

from __future__ import annotations

from collections import Counter
import hashlib
from importlib.metadata import version
import json
import os
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
from pathlib import Path
import platform
import statistics
import sys
import time

import faiss
import numpy as np
import psutil
import torch
from FlagEmbedding import BGEM3FlagModel
from sentence_transformers import SentenceTransformer
from transformers import AutoTokenizer


ROOT = Path(__file__).resolve().parents[1]
RETRIEVAL_DIR = ROOT / "retrieval"
EVALUATION_DIR = ROOT / "evaluation"
SCHEMA_DOCUMENTS_PATH = ROOT / "schema_extraction" / "schema_documents.json"
MINILM_INDEX_PATH = RETRIEVAL_DIR / "schema.index"
MINILM_METADATA_PATH = RETRIEVAL_DIR / "schema_metadata.pkl"
INDEX_PATH = RETRIEVAL_DIR / "bge_m3_schema.index"
METADATA_PATH = RETRIEVAL_DIR / "bge_m3_schema_metadata.json"
BUILD_REPORT_PATH = RETRIEVAL_DIR / "bge_m3_schema_build_report.json"
MANIFEST_PATH = RETRIEVAL_DIR / "bge_m3_model_manifest.json"
COVERAGE_PATH = EVALUATION_DIR / "bge_m3_document_coverage.json"
PROTECTED_HASHES_PATH = EVALUATION_DIR / "bge_m3_protected_hashes_before.json"
LATE_FIELD_SOURCE_PATH = EVALUATION_DIR / "chunked_truncation_hypothesis.json"

MODEL_REPOSITORY = "BAAI/bge-m3"
MODEL_REVISION = "5617a9f61b028005a4858fdac845db406aefb181"
MODEL_WEIGHT_SHA256 = "b5e0ce3470abf5ef3831aa1bd5553b486803e83251590ab7ff35a117cf6aad38"
MINILM_REPOSITORY = "sentence-transformers/all-MiniLM-L6-v2"
MAX_ENCODED_TOKENS = 8192
BATCH_SIZE = 1
EMBEDDING_DIMENSION = 1024
EXPECTED_DOCUMENTS = 2196
DEVICE = "cpu"
PRECISION = "float32"
CPU_THREADS = 8

os.environ.setdefault("OMP_NUM_THREADS", str(CPU_THREADS))
os.environ.setdefault("MKL_NUM_THREADS", str(CPU_THREADS))
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
torch.set_num_threads(CPU_THREADS)
torch.set_num_interop_threads(1)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def write_json(path: Path, value) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def protected_paths() -> list[Path]:
    explicit = [
        SCHEMA_DOCUMENTS_PATH,
        MINILM_INDEX_PATH,
        MINILM_METADATA_PATH,
        RETRIEVAL_DIR / "retriever.py",
        RETRIEVAL_DIR / "hybrid_retriever.py",
        RETRIEVAL_DIR / "graph_expanded_retriever.py",
        RETRIEVAL_DIR / "erp_retrieval_benchmark.py",
        RETRIEVAL_DIR / "erp_retrieval_heldout_benchmark.py",
        EVALUATION_DIR / "real_world_text2sql_benchmark.py",
        EVALUATION_DIR / "text2sql_gold_benchmark.py",
        EVALUATION_DIR / "gold_sql_definitions.py",
        EVALUATION_DIR / "text2sql_gold_validation.json",
        EVALUATION_DIR / "TEXT2SQL_GOLD_VALIDATION.md",
        EVALUATION_DIR / "real_world_gold_benchmark.py",
        EVALUATION_DIR / "real_world_gold_validation.json",
        EVALUATION_DIR / "REAL_WORLD_GOLD_VALIDATION.md",
        RETRIEVAL_DIR / "business_alias_source.json",
        RETRIEVAL_DIR / "business_alias_catalog.json",
        RETRIEVAL_DIR / "business_alias_translation_queue.json",
        RETRIEVAL_DIR / "build_chunked_schema_index.py",
        RETRIEVAL_DIR / "chunked_retriever.py",
        RETRIEVAL_DIR / "chunked_schema.index",
        RETRIEVAL_DIR / "chunked_schema_metadata.json",
        RETRIEVAL_DIR / "chunked_schema_index_build_report.json",
        EVALUATION_DIR / "run_chunked_retrieval_comparison.py",
        EVALUATION_DIR / "chunked_retrieval_comparison_results.json",
        LATE_FIELD_SOURCE_PATH,
    ]
    missing = [str(path.relative_to(ROOT)) for path in explicit if not path.is_file()]
    if missing:
        raise FileNotFoundError(f"Protected files missing: {missing}")
    return explicit


def record_protected_hashes() -> dict[str, str]:
    hashes = {
        str(path.relative_to(ROOT)): sha256_file(path)
        for path in protected_paths()
    }
    write_json(PROTECTED_HASHES_PATH, {
        "status": "frozen_before_bge_model_load_document_encoding_or_evaluation",
        "sha256": hashes,
    })
    return hashes


def content_tokenization(tokenizer, text: str):
    encoded = tokenizer(
        text,
        add_special_tokens=False,
        truncation=False,
        return_offsets_mapping=True,
    )
    return encoded["input_ids"], encoded["offset_mapping"]


def retained_endpoint(offsets, retained_count: int) -> int:
    if not offsets or retained_count <= 0:
        return 0
    return int(offsets[min(retained_count, len(offsets)) - 1][1])


def classify_new_span(text: str, start: int, end: int) -> dict[str, int]:
    """Describe newly retained source records without storing their text."""
    counts = Counter({
        "additional_column_definitions": 0,
        "outgoing_relationship_content": 0,
        "incoming_reference_content": 0,
        "other_original_schema_text": 0,
    })
    if end <= start:
        return dict(counts)
    relationships_at = text.find("\n\nRelationships:\n")
    cursor = 0
    for line in text.splitlines(keepends=True):
        line_start, line_end = cursor, cursor + len(line)
        cursor = line_end
        if line_end <= start or line_start >= end or not line.strip():
            continue
        if relationships_at < 0 or line_start < relationships_at:
            if line.lstrip().startswith("- "):
                counts["additional_column_definitions"] += 1
            else:
                counts["other_original_schema_text"] += 1
        elif "FOREIGN KEY" in line.upper():
            counts["outgoing_relationship_content"] += 1
        elif " references " in line.lower():
            counts["incoming_reference_content"] += 1
        else:
            counts["other_original_schema_text"] += 1
    return dict(counts)


def token_position_for_character(offsets, position: int) -> int | None:
    for index, (_, end) in enumerate(offsets, start=1):
        if end > position:
            return index
    return None


def build_coverage(documents, minilm_tokenizer, bge_tokenizer):
    mini_specials = minilm_tokenizer.num_special_tokens_to_add(pair=False)
    bge_specials = bge_tokenizer.num_special_tokens_to_add(pair=False)
    mini_allowance = 256 - mini_specials
    bge_allowance = MAX_ENCODED_TOKENS - bge_specials
    if mini_allowance != 254:
        raise ValueError(f"Unexpected MiniLM content allowance: {mini_allowance}")
    if bge_allowance <= 0:
        raise ValueError("BGE tokenizer leaves no content allowance")

    rows = []
    coverage_by_table = {}
    token_cache = {}
    hypothesis = json.loads(LATE_FIELD_SOURCE_PATH.read_text(encoding="utf-8"))
    late_tables = {entry["table"] for entry in hypothesis["entries"]}
    late_offsets = {}
    for document in documents:
        text = document["text"]
        mini_ids, mini_offsets = content_tokenization(minilm_tokenizer, text)
        bge_ids, bge_offsets = content_tokenization(bge_tokenizer, text)
        mini_retained = min(len(mini_ids), mini_allowance)
        bge_retained = min(len(bge_ids), bge_allowance)
        mini_endpoint = retained_endpoint(mini_offsets, mini_retained)
        bge_endpoint = retained_endpoint(bge_offsets, bge_retained)
        text_length = len(text)
        row = {
            "fully_qualified_table": document["full_name"],
            "document_sha256": sha256_text(text),
            "document_characters": text_length,
            "minilm": {
                "tokenizer": MINILM_REPOSITORY,
                "full_content_token_count": len(mini_ids),
                "retained_content_token_count": mini_retained,
                "encoded_token_count": mini_retained + mini_specials,
                "truncated": len(mini_ids) > mini_allowance,
                "retained_token_percentage_within_tokenizer": (
                    100.0 * mini_retained / len(mini_ids) if mini_ids else 100.0
                ),
                "approximate_retained_character_endpoint": mini_endpoint,
                "original_text_character_coverage_percentage": (
                    100.0 * mini_endpoint / text_length if text_length else 100.0
                ),
            },
            "bge_m3": {
                "tokenizer": MODEL_REPOSITORY,
                "full_content_token_count": len(bge_ids),
                "retained_content_token_count": bge_retained,
                "encoded_token_count": bge_retained + bge_specials,
                "truncated": len(bge_ids) > bge_allowance,
                "retained_token_percentage_within_tokenizer": (
                    100.0 * bge_retained / len(bge_ids) if bge_ids else 100.0
                ),
                "approximate_retained_character_endpoint": bge_endpoint,
                "original_text_character_coverage_percentage": (
                    100.0 * bge_endpoint / text_length if text_length else 100.0
                ),
            },
            "newly_retained_bge_source_record_counts": classify_new_span(
                text, mini_endpoint, bge_endpoint
            ),
        }
        rows.append(row)
        coverage_by_table[document["full_name"]] = row
        token_cache[document["full_name"]] = {
            "bge_content_ids": bge_ids[:bge_allowance],
        }
        if document["full_name"] in late_tables:
            late_offsets[document["full_name"]] = {
                "mini": mini_offsets,
                "bge": bge_offsets,
            }

    documents_by_name = {item["full_name"]: item for item in documents}
    late_fields = []
    for source in hypothesis["entries"]:
        table = source["table"]
        marker = source["source_evidence"]["marker"]
        text = documents_by_name[table]["text"]
        character_position = text.find(marker)
        if character_position < 0:
            raise ValueError(f"Frozen late-field marker disappeared: {table} {marker}")
        mini_position = token_position_for_character(
            late_offsets[table]["mini"], character_position
        )
        bge_position = token_position_for_character(
            late_offsets[table]["bge"], character_position
        )
        mini_retained = mini_position is not None and mini_position <= mini_allowance
        bge_retained = bge_position is not None and bge_position <= bge_allowance
        late_fields.append({
            "table": table,
            "field": source["field"],
            "source_hypothesis_sha256": sha256_file(LATE_FIELD_SOURCE_PATH),
            "minilm_content_token_position_1_based": mini_position,
            "bge_m3_content_token_position_1_based": bge_position,
            "minilm_retained": mini_retained,
            "bge_m3_retained": bge_retained,
            "newly_exposed_by_bge_m3": bge_retained and not mini_retained,
        })

    opaque_diagnostics = [
        {
            "case_id": "REAL-C01",
            "business_concept": "accounting activity and project dimension",
            "physical_tables": [
                "gnd_fiaci.tblTrans", "gnd_fiaci.tblTransDetail",
                "gnd_fiaci.tblTransDetailDetail",
            ],
        },
        {
            "case_id": "REAL-C04",
            "business_concept": "import process terminology",
            "physical_tables": [],
            "table_set_source": "frozen REAL-C04 expected_tables",
        },
        {
            "case_id": "REAL-C05",
            "business_concept": "warehouse issue",
            "physical_tables": ["gnd_scinv.tblExit", "gnd_scinv.tblExitDetail"],
        },
        {
            "case_id": "REAL-C07",
            "business_concept": "employee settlement statement",
            "physical_tables": ["gnd_hrpyr.tblBonusBill"],
        },
        {
            "case_id": "REAL-C08",
            "business_concept": "yarn group and packaging",
            "physical_tables": ["gnd_pjprj.tblInterweaving"],
        },
    ]
    coverage = {
        "status": "frozen_before_benchmark_retrieval_evaluation",
        "document_count": len(rows),
        "tokenizer_comparison_warning": (
            "Token counts are reported separately and are not directly comparable "
            "across the MiniLM and BGE-M3 tokenizers."
        ),
        "limits": {
            "minilm_max_encoded_tokens": 256,
            "minilm_required_special_tokens": mini_specials,
            "minilm_content_allowance": mini_allowance,
            "bge_m3_max_encoded_tokens": MAX_ENCODED_TOKENS,
            "bge_m3_required_special_tokens": bge_specials,
            "bge_m3_content_allowance": bge_allowance,
            "truncation_side": "right",
        },
        "documents": rows,
        "frozen_late_field_coverage": late_fields,
        "frozen_opaque_identifier_diagnostics": opaque_diagnostics,
    }
    write_json(COVERAGE_PATH, coverage)
    return coverage, coverage_by_table, token_cache, bge_allowance


def resolve_model_path() -> Path:
    configured = os.environ.get("BGE_M3_MODEL_PATH")
    if not configured:
        raise RuntimeError(
            "BGE_M3_MODEL_PATH must name the locally cached immutable snapshot"
        )
    path = Path(configured).resolve()
    required = [
        "config.json", "tokenizer.json", "tokenizer_config.json",
        "sentencepiece.bpe.model", "pytorch_model.bin",
        "sparse_linear.pt", "colbert_linear.pt",
    ]
    missing = [name for name in required if not (path / name).is_file()]
    if missing:
        raise FileNotFoundError(f"Pinned model snapshot incomplete: {missing}")
    actual_weight_hash = sha256_file(path / "pytorch_model.bin")
    if actual_weight_hash != MODEL_WEIGHT_SHA256:
        raise ValueError(
            "Pinned model weight hash mismatch: "
            f"{actual_weight_hash} != {MODEL_WEIGHT_SHA256}"
        )
    return path


def load_model(model_path: Path):
    started = time.perf_counter()
    model = BGEM3FlagModel(
        str(model_path),
        devices=DEVICE,
        use_fp16=False,
        use_bf16=False,
        normalize_embeddings=True,
        pooling_method="cls",
        query_instruction_for_retrieval=None,
        batch_size=BATCH_SIZE,
        query_max_length=MAX_ENCODED_TOKENS,
        passage_max_length=MAX_ENCODED_TOKENS,
        return_dense=True,
        return_sparse=False,
        return_colbert_vecs=False,
        local_files_only=True,
    )
    model.model.float()
    model.model.to(DEVICE)
    model.model.eval()
    return model, time.perf_counter() - started


def official_dense_encode(model, text: str) -> np.ndarray:
    output = model.encode_queries(
        [text],
        batch_size=BATCH_SIZE,
        max_length=MAX_ENCODED_TOKENS,
        return_dense=True,
        return_sparse=False,
        return_colbert_vecs=False,
    )
    if output["lexical_weights"] is not None or output["colbert_vecs"] is not None:
        raise ValueError("Sparse or ColBERT output was unexpectedly enabled")
    return np.asarray(output["dense_vecs"], dtype=np.float32)


def preflight(model) -> dict:
    if model.query_max_length != MAX_ENCODED_TOKENS:
        raise ValueError(f"Query max length is {model.query_max_length}, not 8192")
    if model.passage_max_length != MAX_ENCODED_TOKENS:
        raise ValueError(
            f"Passage max length is {model.passage_max_length}, not 8192"
        )
    if model.tokenizer.model_max_length < MAX_ENCODED_TOKENS:
        raise ValueError("Tokenizer does not support the frozen 8192-token limit")
    sample = "Nonbenchmark preflight sentence for validating dense encoding."
    with torch.inference_mode():
        vectors = official_dense_encode(model, sample)
    if vectors.shape != (1, EMBEDDING_DIMENSION):
        raise ValueError(f"Unexpected preflight shape: {vectors.shape}")
    if not np.isfinite(vectors).all():
        raise ValueError("Preflight produced non-finite values")
    normalized = vectors / np.linalg.norm(vectors, axis=1, keepdims=True)
    norm = float(np.linalg.norm(normalized[0]))
    if not np.isclose(norm, 1.0, atol=1e-5):
        raise ValueError(f"Preflight normalization failed: {norm}")
    return {
        "success": True,
        "sample_kind": "nonbenchmark_synthetic_string",
        "dense_embedding_dimension": int(vectors.shape[1]),
        "finite": True,
        "l2_normalized": True,
        "normalized_vector_norm": norm,
        "explicit_max_encoded_tokens": MAX_ENCODED_TOKENS,
        "sparse_output": False,
        "colbert_output": False,
    }


def freeze_manifest(model_path: Path, model, model_load_seconds: float, preflight_result):
    tokenizer = model.tokenizer
    config = json.loads((model_path / "config.json").read_text(encoding="utf-8"))
    tokenizer_config = json.loads(
        (model_path / "tokenizer_config.json").read_text(encoding="utf-8")
    )
    memory = psutil.virtual_memory()
    model_files = [
        "pytorch_model.bin", "sparse_linear.pt", "colbert_linear.pt",
    ]
    tokenizer_files = [
        "tokenizer.json", "tokenizer_config.json", "special_tokens_map.json",
        "sentencepiece.bpe.model",
    ]
    manifest = {
        "status": "frozen_before_document_encoding_and_benchmark_evaluation",
        "model_repository": MODEL_REPOSITORY,
        "resolved_model_revision": MODEL_REVISION,
        "tokenizer_revision": MODEL_REVISION,
        "resolved_model_path": str(model_path),
        "source_provenance": {
            "provider": "Hugging Face Hub",
            "repository": MODEL_REPOSITORY,
            "immutable_revision": MODEL_REVISION,
            "official_pytorch_weight_sha256": MODEL_WEIGHT_SHA256,
        },
        "versions": {
            "FlagEmbedding": version("FlagEmbedding"),
            "transformers": version("transformers"),
            "torch": torch.__version__,
            "faiss": getattr(faiss, "__version__", version("faiss-cpu")),
            "python": platform.python_version(),
        },
        "system": {
            "operating_system": platform.platform(),
            "cpu": platform.processor() or os.environ.get("PROCESSOR_IDENTIFIER"),
            "logical_cpu_count": os.cpu_count(),
            "torch_intraop_threads": torch.get_num_threads(),
            "torch_interop_threads": torch.get_num_interop_threads(),
            "total_ram_bytes": memory.total,
            "available_ram_bytes_at_manifest": memory.available,
        },
        "frozen_encoding": {
            "representation": "one exact original schema document per table",
            "official_implementation": "FlagEmbedding.BGEM3FlagModel",
            "dense_only": True,
            "pooling": "cls",
            "normalize_embeddings": True,
            "precision": PRECISION,
            "device": DEVICE,
            "batch_size": BATCH_SIZE,
            "cpu_threads": CPU_THREADS,
            "maximum_encoded_tokens_including_special_tokens": MAX_ENCODED_TOKENS,
            "required_special_tokens": tokenizer.num_special_tokens_to_add(pair=False),
            "truncation_side": "right",
            "query_instruction_prefix": None,
            "embedding_dimension": EMBEDDING_DIMENSION,
            "sparse_output": False,
            "colbert_output": False,
        },
        "model_config": config,
        "tokenizer_configuration": {
            **tokenizer_config,
            "runtime_model_max_length": tokenizer.model_max_length,
            "runtime_truncation_side": tokenizer.truncation_side,
            "runtime_special_tokens_map": tokenizer.special_tokens_map,
        },
        "file_sha256": {
            "model": {
                name: sha256_file(model_path / name) for name in model_files
            },
            "tokenizer": {
                name: sha256_file(model_path / name)
                for name in tokenizer_files if (model_path / name).is_file()
            },
        },
        "model_load_seconds": model_load_seconds,
        "setup_download_seconds": None,
        "setup_download_timing_note": (
            "Package installation and resumable checkpoint download occurred "
            "before the instrumented build process and were not timed comparably."
        ),
        "preflight": preflight_result,
    }
    write_json(MANIFEST_PATH, manifest)
    return manifest


def prepared_dense_encode(model, content_ids: list[int]) -> np.ndarray:
    """Run official M3 dense forward pass over preserved truncated token IDs."""
    tokenizer = model.tokenizer
    if (
        tokenizer.num_special_tokens_to_add(pair=False) != 2
        or tokenizer.cls_token_id is None
        or tokenizer.sep_token_id is None
    ):
        raise ValueError("Unexpected BGE-M3 single-sequence special-token format")
    input_ids = [tokenizer.cls_token_id, *content_ids, tokenizer.sep_token_id]
    attention_mask = [1] * len(input_ids)
    if len(input_ids) > MAX_ENCODED_TOKENS:
        raise ValueError("Prepared document exceeded the frozen 8192-token limit")
    inputs = {
        "input_ids": torch.tensor([input_ids], dtype=torch.long),
        "attention_mask": torch.tensor([attention_mask], dtype=torch.long),
    }
    with torch.inference_mode():
        output = model.model(
            inputs,
            return_dense=True,
            return_sparse=False,
            return_colbert_vecs=False,
            truncate_dim=None,
        )
    vector = output["dense_vecs"].detach().cpu().numpy().astype(np.float32)[0]
    if vector.shape != (EMBEDDING_DIMENSION,) or not np.isfinite(vector).all():
        raise ValueError("Invalid BGE document embedding")
    norm = np.linalg.norm(vector)
    if norm == 0.0:
        raise ValueError("Zero BGE document embedding")
    vector /= norm
    return vector


def distribution(values) -> dict:
    return {
        "minimum": min(values),
        "median": statistics.median(values),
        "mean": statistics.mean(values),
        "maximum": max(values),
    }


def main() -> None:
    protected_hashes = record_protected_hashes()
    model_path = resolve_model_path()
    documents = json.loads(SCHEMA_DOCUMENTS_PATH.read_text(encoding="utf-8"))
    if len(documents) != EXPECTED_DOCUMENTS:
        raise ValueError(f"Expected 2196 documents, found {len(documents)}")
    if len({item["full_name"] for item in documents}) != EXPECTED_DOCUMENTS:
        raise ValueError("Original corpus contains duplicate table identities")

    model, model_load_seconds = load_model(model_path)
    preflight_result = preflight(model)
    manifest = freeze_manifest(
        model_path, model, model_load_seconds, preflight_result
    )

    minilm_model = SentenceTransformer(MINILM_REPOSITORY, device="cpu")
    minilm_tokenizer = minilm_model.tokenizer
    del minilm_model
    bge_tokenizer = model.tokenizer
    coverage, coverage_by_table, token_cache, content_allowance = build_coverage(
        documents, minilm_tokenizer, bge_tokenizer
    )

    process = psutil.Process()
    observed_peak_rss = process.memory_info().rss
    vectors = np.empty((EXPECTED_DOCUMENTS, EMBEDDING_DIMENSION), dtype=np.float32)
    started = time.perf_counter()
    for vector_id, document in enumerate(documents):
        vectors[vector_id] = prepared_dense_encode(
            model, token_cache[document["full_name"]]["bge_content_ids"]
        )
        observed_peak_rss = max(observed_peak_rss, process.memory_info().rss)
        if (vector_id + 1) % 25 == 0 or vector_id + 1 == EXPECTED_DOCUMENTS:
            elapsed = time.perf_counter() - started
            print(
                f"Encoded {vector_id + 1}/{EXPECTED_DOCUMENTS} documents "
                f"in {elapsed:.1f}s",
                flush=True,
            )
    embedding_seconds = time.perf_counter() - started

    norms = np.linalg.norm(vectors, axis=1)
    if not np.isfinite(vectors).all():
        raise ValueError("BGE index vectors include non-finite values")
    if not np.allclose(norms, 1.0, atol=1e-5):
        raise ValueError("BGE index vectors are not L2 normalized")

    index_started = time.perf_counter()
    index = faiss.IndexFlatIP(EMBEDDING_DIMENSION)
    index.add(vectors)
    faiss.write_index(index, str(INDEX_PATH))
    faiss_seconds = time.perf_counter() - index_started

    mapping = []
    for vector_id, document in enumerate(documents):
        row = coverage_by_table[document["full_name"]]
        mapping.append({
            "vector_id": vector_id,
            "fully_qualified_table": document["full_name"],
            "schema": document["schema"],
            "physical_table_name": document["table_name"],
            "document_sha256": row["document_sha256"],
            "full_content_token_count": row["bge_m3"]["full_content_token_count"],
            "retained_content_token_count": row["bge_m3"]["retained_content_token_count"],
            "encoded_token_count": row["bge_m3"]["encoded_token_count"],
            "truncated": row["bge_m3"]["truncated"],
        })
    write_json(METADATA_PATH, {
        "format_version": 1,
        "experiment": "frozen_bge_m3_dense_long_context",
        "model_repository": MODEL_REPOSITORY,
        "model_revision": MODEL_REVISION,
        "maximum_encoded_tokens": MAX_ENCODED_TOKENS,
        "content_allowance": content_allowance,
        "vector_dimension": EMBEDDING_DIMENSION,
        "mapping": mapping,
    })

    report = {
        "experiment": "frozen_bge_m3_dense_long_context",
        "document_count": len(documents),
        "vector_count": index.ntotal,
        "vector_dimension": index.d,
        "all_vectors_finite": bool(np.isfinite(vectors).all()),
        "all_vectors_l2_normalized": bool(np.allclose(norms, 1.0, atol=1e-5)),
        "vector_norm_distribution": distribution(norms.tolist()),
        "maximum_encoded_tokens": MAX_ENCODED_TOKENS,
        "maximum_observed_encoded_tokens": max(
            row["bge_m3"]["encoded_token_count"]
            for row in coverage["documents"]
        ),
        "truncated_document_count": sum(
            row["bge_m3"]["truncated"] for row in coverage["documents"]
        ),
        "model_load_seconds": model_load_seconds,
        "document_embedding_build_seconds": embedding_seconds,
        "faiss_build_write_seconds": faiss_seconds,
        "observed_peak_process_rss_bytes": observed_peak_rss,
        "model_disk_size_bytes": sum(
            path.stat().st_size for path in model_path.iterdir() if path.is_file()
        ),
        "embedding_vector_payload_bytes": vectors.nbytes,
        "faiss_index_size_bytes": INDEX_PATH.stat().st_size,
        "metadata_size_bytes": METADATA_PATH.stat().st_size,
        "manifest_sha256": sha256_file(MANIFEST_PATH),
        "coverage_sha256": sha256_file(COVERAGE_PATH),
        "protected_hashes_sha256": sha256_file(PROTECTED_HASHES_PATH),
        "artifacts_sha256": {
            str(INDEX_PATH.relative_to(ROOT)): sha256_file(INDEX_PATH),
            str(METADATA_PATH.relative_to(ROOT)): sha256_file(METADATA_PATH),
        },
        "integrity": {
            "original_order_preserved": all(
                mapping[index]["fully_qualified_table"] == document["full_name"]
                for index, document in enumerate(documents)
            ),
            "protected_files_still_match": protected_hashes == {
                str(path.relative_to(ROOT)): sha256_file(path)
                for path in protected_paths()
            },
            "model_revision_matches_manifest": (
                manifest["resolved_model_revision"] == MODEL_REVISION
            ),
        },
    }
    write_json(BUILD_REPORT_PATH, report)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
