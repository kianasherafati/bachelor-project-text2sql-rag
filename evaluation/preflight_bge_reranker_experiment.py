"""Read-only preflight for the frozen BGE reranker experiment."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import statistics
import sys


ROOT = Path(__file__).resolve().parents[1]
RETRIEVAL = ROOT / "retrieval"
sys.path.insert(0, str(RETRIEVAL))
sys.path.insert(0, str(ROOT / "evaluation"))

from bge_reranker_v2_m3 import (  # noqa: E402
    DOCUMENT_BUDGET,
    MAX_PAIR_LENGTH,
    QUESTION_BUDGET,
    load_tokenizer,
)
from erp_retrieval_benchmark import tests as development_tests  # noqa: E402
from erp_retrieval_heldout_benchmark import tests as heldout_tests  # noqa: E402
from real_world_text2sql_benchmark import tests as real_world_tests  # noqa: E402


CANDIDATES_PATH = ROOT / "evaluation" / "bge_reranker_candidate_lists.json"
REPRESENTATIONS_PATH = RETRIEVAL / "bge_reranker_table_representations.json"
AUDIT_PATH = RETRIEVAL / "bge_reranker_representation_audit.json"
IDENTITY_PATH = RETRIEVAL / "bge_reranker_identity_preflight.json"
BUILD_REPORT_PATH = RETRIEVAL / "bge_reranker_representation_build_report.json"
MANIFEST_PATH = RETRIEVAL / "bge_reranker_v2_m3_manifest.json"
OUTPUT_PATH = ROOT / "evaluation" / "bge_reranker_pair_preflight.json"

SUITES = {
    "development_9": development_tests,
    "heldout_schema_20": heldout_tests,
    "real_world_observed_13": real_world_tests,
}
EXPECTED_COVERAGE = {
    "development_9": (1.0, 9, 635),
    "heldout_schema_20": (0.9833333333333333, 19, 1369),
    "real_world_observed_13": (0.6419413919413919, 6, 927),
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> None:
    candidates = json.loads(CANDIDATES_PATH.read_text(encoding="utf-8"))
    representations = json.loads(REPRESENTATIONS_PATH.read_text(encoding="utf-8"))
    audit = json.loads(AUDIT_PATH.read_text(encoding="utf-8"))
    identity = json.loads(IDENTITY_PATH.read_text(encoding="utf-8"))
    report = json.loads(BUILD_REPORT_PATH.read_text(encoding="utf-8"))
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))

    if candidates["candidate_policy"]["bge_dense_depth"] != 50:
        raise RuntimeError("BGE candidate depth changed")
    if candidates["candidate_policy"]["minilm_graph_output_depth"] != 50:
        raise RuntimeError("MiniLM Graph candidate depth changed")
    if candidates["combined_candidate_count"]["total_pairs"] != 2931:
        raise RuntimeError("Combined candidate pair count changed")
    if len(representations["tables"]) != 2196 or len(audit["tables"]) != 2196:
        raise RuntimeError("Representation count is not 2,196")
    if representations["section_budgets"] != {
        "identity": 68,
        "table_labels": 96,
        "associated_forms": 128,
        "modules": 64,
        "columns": 536,
    }:
        raise RuntimeError("Section budgets differ from the frozen revision")
    if representations["document_budget"] != DOCUMENT_BUDGET or DOCUMENT_BUDGET != 892:
        raise RuntimeError("Document budget changed")
    if identity["status"] != "passed" or identity["tables_exceeding_budget"]:
        raise RuntimeError("Identity preflight is not clean")
    if not report["deterministic_rebuild_match"]:
        raise RuntimeError("Representation determinism check failed")
    if sha256_file(REPRESENTATIONS_PATH) != report["representations_sha256"]:
        raise RuntimeError("Representation artifact hash mismatch")
    if sha256_file(AUDIT_PATH) != report["audit_sha256"]:
        raise RuntimeError("Representation audit hash mismatch")
    for relative, expected_hash in candidates["protected_sha256"].items():
        if sha256_file(ROOT / relative) != expected_hash:
            raise RuntimeError(f"Frozen protected file changed: {relative}")
    frozen = manifest["frozen_inference"]
    if (
        frozen["precision"] != "float32"
        or frozen["device"] != "cpu"
        or frozen["batch_size"] != 1
        or frozen["max_pair_tokens_including_special_tokens"] != MAX_PAIR_LENGTH
        or frozen["question_budget_without_special_tokens"] != QUESTION_BUDGET
    ):
        raise RuntimeError("Frozen inference configuration changed")

    tokenizer = load_tokenizer()
    by_table = {item["fully_qualified_table"]: item for item in representations["tables"]}
    question_tokens = []
    document_tokens = []
    pair_tokens = []
    exactly_maximum = 0
    exceeding = []
    seen_pairs = set()
    case_count = 0

    for suite_name, benchmark_cases in SUITES.items():
        stored_suite = candidates["suites"][suite_name]
        expected_recall, expected_full, expected_pairs = EXPECTED_COVERAGE[suite_name]
        coverage = stored_suite["coverage"]
        if abs(coverage["macro_candidate_recall"] - expected_recall) > 1e-12:
            raise RuntimeError(f"{suite_name} candidate recall changed")
        if coverage["full_coverage_count"] != expected_full:
            raise RuntimeError(f"{suite_name} full coverage changed")
        if stored_suite["candidate_count"]["total_pairs"] != expected_pairs:
            raise RuntimeError(f"{suite_name} candidate pair count changed")
        if len(stored_suite["cases"]) != len(benchmark_cases):
            raise RuntimeError(f"{suite_name} case count changed")
        for case_index, (stored_case, benchmark_case) in enumerate(
            zip(stored_suite["cases"], benchmark_cases), start=1
        ):
            case_count += 1
            expected_id = (
                f"DEV-{case_index:02d}"
                if suite_name == "development_9"
                else benchmark_case["id"]
            )
            if stored_case["id"] != expected_id:
                raise RuntimeError(f"Case ordering or ID changed for {suite_name}")
            if stored_case["question"] != benchmark_case["question"]:
                raise RuntimeError(f"Question changed for {stored_case['id']}")
            if stored_case["expected_tables"] != benchmark_case["expected_tables"]:
                raise RuntimeError(f"Expected tables changed for {stored_case['id']}")
            q_tokens = len(tokenizer.encode(stored_case["question"], add_special_tokens=False))
            question_tokens.append(q_tokens)
            if q_tokens > QUESTION_BUDGET:
                raise RuntimeError(f"Question budget exceeded for {stored_case['id']}")
            candidate_tables = [item["table"] for item in stored_case["union_candidates"]]
            if candidate_tables != sorted(set(candidate_tables)):
                raise RuntimeError(f"Candidate ordering/deduplication changed for {stored_case['id']}")
            for table in candidate_tables:
                key = (suite_name, stored_case["id"], table)
                if key in seen_pairs:
                    raise RuntimeError(f"Duplicate candidate pair: {key}")
                seen_pairs.add(key)
                representation = by_table[table]
                d_tokens = len(tokenizer.encode(representation["text"], add_special_tokens=False))
                if d_tokens != representation["token_count"] or d_tokens > DOCUMENT_BUDGET:
                    raise RuntimeError(f"Document token audit mismatch for {table}")
                document_tokens.append(d_tokens)
                encoded = tokenizer(
                    stored_case["question"],
                    representation["text"],
                    add_special_tokens=True,
                    truncation=False,
                    padding=False,
                    return_attention_mask=False,
                    return_token_type_ids=False,
                )
                count = len(encoded["input_ids"])
                pair_tokens.append(count)
                if count == MAX_PAIR_LENGTH:
                    exactly_maximum += 1
                if count > MAX_PAIR_LENGTH:
                    exceeding.append({"case_id": stored_case["id"], "table": table, "tokens": count})

    if case_count != 42 or len(seen_pairs) != 2931:
        raise RuntimeError("Expected exactly 42 cases and 2,931 unique pairs")
    if exceeding:
        raise RuntimeError(f"Pair-length preflight failed: {exceeding[:3]}")
    output = {
        "status": "passed",
        "case_count": case_count,
        "unique_candidate_pairs": len(seen_pairs),
        "candidate_source_depths": {"bge_dense": 50, "minilm_graph": 50},
        "candidate_coverage": {
            name: candidates["suites"][name]["coverage"] for name in SUITES
        },
        "token_limits": {
            "identity": 68,
            "columns": 536,
            "document": DOCUMENT_BUDGET,
            "question": QUESTION_BUDGET,
            "pair": MAX_PAIR_LENGTH,
            "special_tokens": tokenizer.num_special_tokens_to_add(pair=True),
        },
        "actual_tokens": {
            "maximum_question": max(question_tokens),
            "maximum_document": max(document_tokens),
            "maximum_pair": max(pair_tokens),
            "pairs_exactly_1024": exactly_maximum,
            "pairs_exceeding_1024": len(exceeding),
            "pair_mean": statistics.mean(pair_tokens),
            "pair_median": statistics.median(pair_tokens),
        },
        "frozen_artifact_sha256": {
            "evaluation\\bge_reranker_candidate_lists.json": sha256_file(CANDIDATES_PATH),
            "retrieval\\bge_reranker_table_representations.json": sha256_file(REPRESENTATIONS_PATH),
            "retrieval\\bge_reranker_representation_audit.json": sha256_file(AUDIT_PATH),
            "retrieval\\bge_reranker_identity_preflight.json": sha256_file(IDENTITY_PATH),
            "retrieval\\bge_reranker_representation_build_report.json": sha256_file(BUILD_REPORT_PATH),
            "retrieval\\bge_reranker_v2_m3_manifest.json": sha256_file(MANIFEST_PATH),
            **candidates["protected_sha256"],
        },
    }
    OUTPUT_PATH.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
