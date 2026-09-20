"""Materialize the frozen BGE-Dense Top-50 union MiniLM Graph Top-50 pool."""

from __future__ import annotations

import gc
import hashlib
import json
import os
from pathlib import Path
import statistics
import sys
import time


ROOT = Path(__file__).resolve().parents[1]
EVAL = ROOT / "evaluation"
RETRIEVAL = ROOT / "retrieval"
OUTPUT = EVAL / "bge_reranker_candidate_lists.json"
sys.path.insert(0, str(EVAL))
sys.path.insert(0, str(RETRIEVAL))
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
os.environ.setdefault("OMP_NUM_THREADS", "8")
os.environ.setdefault("MKL_NUM_THREADS", "8")

from bge_m3_retriever import BGEM3SchemaRetriever
from erp_retrieval_benchmark import tests as development_tests
from erp_retrieval_heldout_benchmark import tests as heldout_tests
from graph_expanded_retriever import (
    FIXED_FK_BONUS,
    HYBRID_SEED_COUNT,
    GraphExpandedSchemaRetriever,
)
from real_world_text2sql_benchmark import tests as real_world_tests


DEPTH = 50
EXPECTED_COVERAGE = {
    "development_9": (1.0000, 9),
    "heldout_schema_20": (0.9833, 19),
    "real_world_observed_13": (0.6419, 6),
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def suites():
    dev = []
    for index, case in enumerate(development_tests, start=1):
        item = dict(case)
        item["id"] = f"DEV-{index:02d}"
        item.setdefault("difficulty", None)
        item.setdefault("domain", None)
        dev.append(item)
    return {
        "development_9": dev,
        "heldout_schema_20": [dict(case) for case in heldout_tests],
        "real_world_observed_13": [dict(case) for case in real_world_tests],
    }


def protected_paths():
    paths = [
        RETRIEVAL / "bge_m3_schema.index",
        RETRIEVAL / "bge_m3_schema_metadata.json",
        RETRIEVAL / "bge_m3_model_manifest.json",
        RETRIEVAL / "schema.index",
        RETRIEVAL / "schema_metadata.pkl",
        RETRIEVAL / "bge_m3_retriever.py",
        RETRIEVAL / "graph_expanded_retriever.py",
        RETRIEVAL / "hybrid_retriever.py",
        RETRIEVAL / "retriever.py",
        RETRIEVAL / "erp_retrieval_benchmark.py",
        RETRIEVAL / "erp_retrieval_heldout_benchmark.py",
        EVAL / "real_world_text2sql_benchmark.py",
    ]
    if any(not path.is_file() for path in paths):
        raise FileNotFoundError("A protected candidate-source artifact is missing")
    return paths


def hashes(paths):
    return {str(path.relative_to(ROOT)): sha256(path) for path in paths}


def dense_item(item, rank):
    return {
        "rank": rank,
        "table": item["full_name"],
        "raw_cosine": item["raw_bge_cosine"],
        "normalized_dense_score": item["dense_score"],
    }


def graph_item(item, rank):
    return {
        "rank": rank,
        "table": item["full_name"],
        "raw_cosine": 2.0 * item["dense_score"] - 1.0,
        "normalized_dense_score": item["dense_score"],
        "lexical_score": item["lexical_score"],
        "hybrid_score": item["hybrid_score"],
        "graph_signal": item["graph_signal"],
        "fk_bonus": item["fk_bonus_contribution"],
        "final_score": item["final_score"],
        "is_hybrid_seed": item["is_hybrid_seed"],
        "source_seed_tables": item["source_seed_tables"],
    }


def coverage(case_rows):
    recalls = []
    full = 0
    for row in case_rows:
        names = {item["table"] for item in row["union_candidates"]}
        hits = sum(table in names for table in row["expected_tables"])
        recalls.append(hits / len(row["expected_tables"]))
        full += hits == len(row["expected_tables"])
    return {
        "macro_candidate_recall": statistics.mean(recalls),
        "full_coverage_count": full,
        "question_count": len(case_rows),
    }


def main():
    definitions = suites()
    paths = protected_paths()
    before = hashes(paths)
    timings = {}

    started = time.perf_counter()
    bge = BGEM3SchemaRetriever()
    bge.warmup()
    dense_by_case = {}
    for cases in definitions.values():
        for case in cases:
            results = bge.retrieve_bge_dense(case["question"], top_k=DEPTH)
            dense_by_case[case["id"]] = [
                dense_item(item, rank)
                for rank, item in enumerate(results, start=1)
            ]
    timings["bge_dense_materialization_seconds"] = time.perf_counter() - started
    del bge
    gc.collect()

    started = time.perf_counter()
    graph = GraphExpandedSchemaRetriever()
    graph_by_case = {}
    graph_pool_sizes = {}
    for cases in definitions.values():
        for case in cases:
            run = graph.retrieve_graph_expanded(case["question"], top_k=DEPTH)
            graph_by_case[case["id"]] = [
                graph_item(item, rank)
                for rank, item in enumerate(run["results"], start=1)
            ]
            graph_pool_sizes[case["id"]] = run["expanded_candidate_pool_size"]
    timings["minilm_graph_materialization_seconds"] = time.perf_counter() - started
    del graph
    gc.collect()

    output_suites = {}
    all_counts = []
    for suite_name, cases in definitions.items():
        rows = []
        for case in cases:
            dense = dense_by_case[case["id"]]
            graph_rows = graph_by_case[case["id"]]
            if len(dense) != DEPTH:
                raise ValueError(f"BGE-Dense did not return 50 rows for {case['id']}")
            union = {}
            for item in dense:
                union.setdefault(item["table"], {})["bge_dense"] = item
            for item in graph_rows:
                union.setdefault(item["table"], {})["minilm_graph"] = item
            union_rows = [
                {
                    "table": table,
                    "sources": sorted(source_data),
                    "bge_dense": source_data.get("bge_dense"),
                    "minilm_graph": source_data.get("minilm_graph"),
                }
                for table, source_data in sorted(union.items())
            ]
            if len(union_rows) != len({item["table"] for item in union_rows}):
                raise ValueError(f"Duplicate union candidate for {case['id']}")
            all_counts.append(len(union_rows))
            rows.append({
                "id": case["id"],
                "question": case["question"],
                "difficulty": case.get("difficulty"),
                "domain": case.get("domain"),
                "expected_tables": list(case["expected_tables"]),
                "bge_dense_top_50": dense,
                "minilm_graph_top_50_or_available": graph_rows,
                "minilm_graph_candidate_pool_size": graph_pool_sizes[case["id"]],
                "union_candidate_count": len(union_rows),
                "union_candidates": union_rows,
            })
        measured = coverage(rows)
        target_recall, target_full = EXPECTED_COVERAGE[suite_name]
        if (
            round(measured["macro_candidate_recall"], 4) != target_recall
            or measured["full_coverage_count"] != target_full
        ):
            raise RuntimeError(
                f"STOP: oracle coverage mismatch for {suite_name}: {measured}"
            )
        output_suites[suite_name] = {
            "coverage": measured,
            "cases": rows,
            "candidate_count": {
                "mean": statistics.mean(row["union_candidate_count"] for row in rows),
                "median": statistics.median(row["union_candidate_count"] for row in rows),
                "minimum": min(row["union_candidate_count"] for row in rows),
                "maximum": max(row["union_candidate_count"] for row in rows),
                "total_pairs": sum(row["union_candidate_count"] for row in rows),
            },
        }

    after = hashes(paths)
    if after != before:
        raise RuntimeError("Protected candidate-source artifact changed")
    payload = {
        "artifact_type": "frozen_bge_reranker_candidate_lists",
        "candidate_policy": {
            "bge_dense_depth": DEPTH,
            "minilm_graph_output_depth": DEPTH,
            "minilm_graph_seed_count": HYBRID_SEED_COUNT,
            "minilm_graph_hops": 1,
            "minilm_graph_direction": "outgoing",
            "minilm_graph_fk_bonus": FIXED_FK_BONUS,
            "deduplication_key": "exact fully-qualified table name",
            "union_truncated_after_deduplication": False,
        },
        "timings": timings,
        "combined_candidate_count": {
            "question_count": len(all_counts),
            "mean": statistics.mean(all_counts),
            "median": statistics.median(all_counts),
            "minimum": min(all_counts),
            "maximum": max(all_counts),
            "total_pairs": sum(all_counts),
        },
        "protected_sha256": before,
        "suites": output_suites,
    }
    OUTPUT.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "coverage": {
            name: suite["coverage"] for name, suite in output_suites.items()
        },
        "combined_candidate_count": payload["combined_candidate_count"],
        "timings": timings,
    }, indent=2))


if __name__ == "__main__":
    main()
