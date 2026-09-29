"""One explicit DEV-01 runtime verification; never imports the final benchmark."""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
import sys
from time import perf_counter


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.adapters import (  # noqa: E402
    FROZEN_CANDIDATE_DEPTH,
    FrozenRetrievalSchemaProvider,
    _load_frozen_retrieval_resources,
)


CANDIDATES = ROOT / "evaluation" / "bge_reranker_candidate_lists.json"
RERANKED = ROOT / "evaluation" / "bge_reranker_comparison_results.json"
PREFLIGHT = ROOT / "evaluation" / "bge_reranker_pair_preflight.json"
BGE_MANIFEST = ROOT / "retrieval" / "bge_m3_model_manifest.json"
RERANKER_MANIFEST = ROOT / "retrieval" / "bge_reranker_v2_m3_manifest.json"
EXPECTED_BGE_REPOSITORY = "BAAI/bge-m3"
EXPECTED_BGE_REVISION = "5617a9f61b028005a4858fdac845db406aefb181"
EXPECTED_RERANKER_REPOSITORY = "BAAI/bge-reranker-v2-m3"
EXPECTED_RERANKER_REVISION = "953dc6f6f85a1b2dbfca4c34a2796e7dde08d41e"


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def verify_frozen_hashes():
    preflight = json.loads(PREFLIGHT.read_text(encoding="utf-8"))
    checked = {}
    for relative, expected in preflight["frozen_artifact_sha256"].items():
        path = ROOT / Path(relative)
        actual = sha256(path)
        if actual != expected:
            raise RuntimeError(f"Frozen artifact hash mismatch: {relative}")
        checked[relative.replace("\\", "/")] = actual
    return checked


def verify_manifests():
    bge = json.loads(BGE_MANIFEST.read_text(encoding="utf-8"))
    reranker = json.loads(RERANKER_MANIFEST.read_text(encoding="utf-8"))
    if (bge["model_repository"], bge["resolved_model_revision"]) != (
        EXPECTED_BGE_REPOSITORY, EXPECTED_BGE_REVISION
    ):
        raise RuntimeError("Frozen BGE-M3 identity mismatch")
    if (reranker["model_repository"], reranker["resolved_model_revision"]) != (
        EXPECTED_RERANKER_REPOSITORY, EXPECTED_RERANKER_REVISION
    ):
        raise RuntimeError("Frozen reranker identity mismatch")
    return bge, reranker


def verify_local_model_files(bge, reranker):
    bge_weight = Path(bge["resolved_model_path"]) / "pytorch_model.bin"
    expected_bge = bge["source_provenance"]["official_pytorch_weight_sha256"]
    if not bge_weight.is_file() or sha256(bge_weight) != expected_bge:
        raise RuntimeError("Local frozen BGE-M3 weight hash mismatch")
    reranker_root = Path(reranker["resolved_model_path"])
    for name, identity in reranker["model_files"].items():
        path = reranker_root / name
        if not path.is_file() or path.stat().st_size != identity["size_bytes"]:
            raise RuntimeError(f"Local frozen reranker file size mismatch: {name}")
        if sha256(path) != identity["sha256"]:
            raise RuntimeError(f"Local frozen reranker file hash mismatch: {name}")


def score_canonical(resources, question, candidate_names):
    scored = []
    started = perf_counter()
    for ordinal, name in enumerate(candidate_names, start=1):
        score, _latency, _tokens = resources.reranker.score(
            question, resources.representations[name]
        )
        scored.append((name, float(score)))
        if ordinal % 10 == 0 or ordinal == len(candidate_names):
            print(json.dumps({
                "event": "canonical_reranker_progress",
                "completed": ordinal,
                "total": len(candidate_names),
                "elapsed_seconds": perf_counter() - started,
            }), flush=True)
    scored.sort(key=lambda item: (-item[1], item[0]))
    return scored[:10]


def main():
    print(json.dumps({"event": "verify_frozen_artifacts"}), flush=True)
    hashes = verify_frozen_hashes()
    bge_manifest, reranker_manifest = verify_manifests()
    verify_local_model_files(bge_manifest, reranker_manifest)

    candidates_payload = json.loads(CANDIDATES.read_text(encoding="utf-8"))
    reranked_payload = json.loads(RERANKED.read_text(encoding="utf-8"))
    saved_case = candidates_payload["suites"]["development_9"]["cases"][0]
    saved_result = reranked_payload["suites"]["development_9"]["cases"][0]
    if saved_case["id"] != "DEV-01" or saved_result["id"] != "DEV-01":
        raise RuntimeError("First saved development case is not DEV-01")
    question = saved_case["question"]
    saved_dense = [item["table"] for item in saved_case["bge_dense_top_50"]]
    saved_graph = [item["table"] for item in saved_case["minilm_graph_top_50_or_available"]]
    saved_union = [item["table"] for item in saved_case["union_candidates"]]
    saved_top10 = [
        (item["table"], float(item["reranker_raw_logit"]))
        for item in saved_result["retrieved_top_10"]
    ]
    if len(saved_dense) != 50 or len(saved_graph) != 50 or len(saved_union) != 79:
        raise RuntimeError("Unexpected saved DEV-01 candidate sizes")

    print(json.dumps({"event": "load_application_resources"}), flush=True)
    provider = FrozenRetrievalSchemaProvider()
    resources = provider._resources()
    if resources is not provider._resources():
        raise RuntimeError("Application resources were reloaded within one process")

    retrieval_path = str(ROOT / "retrieval")
    if retrieval_path not in sys.path:
        raise RuntimeError("Frozen retrieval module path missing")
    from bge_m3_retriever import MODEL_REPOSITORY, MODEL_REVISION
    from bge_reranker_v2_m3 import REPOSITORY, REVISION
    from retriever import EMBEDDING_MODEL_NAME

    if (MODEL_REPOSITORY, MODEL_REVISION) != (
        EXPECTED_BGE_REPOSITORY, EXPECTED_BGE_REVISION
    ):
        raise RuntimeError("Loaded BGE-M3 module identity mismatch")
    if (REPOSITORY, REVISION) != (
        EXPECTED_RERANKER_REPOSITORY, EXPECTED_RERANKER_REVISION
    ):
        raise RuntimeError("Loaded reranker module identity mismatch")
    if EMBEDDING_MODEL_NAME != "sentence-transformers/all-MiniLM-L6-v2":
        raise RuntimeError("Loaded MiniLM identity mismatch")

    print(json.dumps({"event": "canonical_candidate_generation"}), flush=True)
    dense = resources.dense_retriever.retrieve_bge_dense(
        question, top_k=FROZEN_CANDIDATE_DEPTH
    )
    graph = resources.graph_retriever.retrieve_graph_expanded(
        question, top_k=FROZEN_CANDIDATE_DEPTH
    )["results"]
    dense_names = [item["full_name"] for item in dense]
    graph_names = [item["full_name"] for item in graph]
    union_names = sorted(set(dense_names).union(graph_names))
    if dense_names != saved_dense:
        raise RuntimeError("Runtime BGE Dense Top50 differs from saved DEV-01")
    if graph_names != saved_graph:
        raise RuntimeError("Runtime MiniLM Graph Top50 differs from saved DEV-01")
    if union_names != saved_union:
        raise RuntimeError("Runtime canonical union differs from saved DEV-01")

    canonical_top10 = score_canonical(resources, question, union_names)
    if [name for name, _score in canonical_top10] != [name for name, _score in saved_top10]:
        raise RuntimeError("Runtime canonical Top10 differs from saved DEV-01")
    if any(not math.isclose(score, saved_score, rel_tol=0.0, abs_tol=0.0)
           for (_name, score), (_saved_name, saved_score) in zip(canonical_top10, saved_top10)):
        raise RuntimeError("Runtime canonical logits differ from saved DEV-01")

    print(json.dumps({"event": "application_adapter_second_request"}), flush=True)
    app_candidates = provider.retrieve(question)
    app_top10 = provider.rerank(question, app_candidates)
    app_pairs = [(item.name, item.score) for item in app_top10]
    if [item.name for item in app_candidates] != union_names:
        raise RuntimeError("Application candidate union differs from canonical runtime")
    if app_pairs != canonical_top10:
        raise RuntimeError("Application Top10 or logits differ from canonical runtime")
    if _load_frozen_retrieval_resources.cache_info().misses != 1:
        raise RuntimeError("Frozen resources initialized more than once")

    minilm_files = (
        "retrieval/schema.index",
        "retrieval/schema_metadata.pkl",
        "retrieval/retriever.py",
        "retrieval/hybrid_retriever.py",
        "retrieval/graph_expanded_retriever.py",
    )
    result = {
        "status": "PASS",
        "case_id": "DEV-01",
        "question": question,
        "candidate_counts": {
            "bge_dense": len(dense_names),
            "minilm_graph": len(graph_names),
            "deduplicated_union": len(union_names),
        },
        "canonical_top10": [
            {"rank": rank, "table": name, "raw_logit": score}
            for rank, (name, score) in enumerate(canonical_top10, start=1)
        ],
        "application_top10": [
            {"rank": item.rank, "table": item.name, "raw_logit": item.score}
            for item in app_top10
        ],
        "exact_match": True,
        "model_identities": {
            "bge_m3": {
                "repository": bge_manifest["model_repository"],
                "revision": bge_manifest["resolved_model_revision"],
            },
            "reranker": {
                "repository": reranker_manifest["model_repository"],
                "revision": reranker_manifest["resolved_model_revision"],
            },
            "minilm": EMBEDDING_MODEL_NAME,
        },
        "minilm_frozen_sha256": {name: hashes[name] for name in minilm_files},
        "resource_cache": {
            "same_object_within_process": True,
            "cache_info": str(_load_frozen_retrieval_resources.cache_info()),
        },
    }
    print(json.dumps(result, ensure_ascii=False, indent=2), flush=True)


if __name__ == "__main__":
    main()
