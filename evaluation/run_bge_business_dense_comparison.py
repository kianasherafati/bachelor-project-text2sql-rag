"""Run the single frozen BGE-Business-Dense candidate-generation experiment."""

from __future__ import annotations

from collections import defaultdict
import hashlib
import json
import math
from pathlib import Path
import statistics
import sys
import time

import psutil


ROOT = Path(__file__).resolve().parents[1]
RETRIEVAL = ROOT / "retrieval"
sys.path.insert(0, str(RETRIEVAL))

from bge_business_dense_retriever import BGEBusinessDenseRetriever  # noqa: E402


CANDIDATES_PATH = ROOT / "evaluation" / "bge_reranker_candidate_lists.json"
RERANKER_RESULTS_PATH = ROOT / "evaluation" / "bge_reranker_comparison_results.json"
REPRESENTATIONS_PATH = RETRIEVAL / "bge_reranker_table_representations.json"
AUDIT_PATH = RETRIEVAL / "bge_reranker_representation_audit.json"
BUILD_REPORT_PATH = RETRIEVAL / "bge_business_schema_build_report.json"
PROTECTED_PATH = ROOT / "evaluation" / "bge_business_dense_protected_hashes_before.json"
OUTPUT_PATH = ROOT / "evaluation" / "bge_business_dense_comparison_results.json"
DEPTHS = [10, 20, 50, 100, 200]
SUITE_ORDER = ["development_9", "heldout_schema_20", "real_world_observed_13"]
CONTROL_TARGETS = {
    "development_9": (1.0, 9),
    "heldout_schema_20": (0.9833333333333333, 19),
    "real_world_observed_13": (0.6419413919413919, 6),
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def percentile(values, fraction):
    ordered = sorted(values)
    return ordered[max(0, math.ceil(fraction * len(ordered)) - 1)]


def timing_distribution(values):
    return {
        "mean": statistics.mean(values),
        "median": statistics.median(values),
        "p95": percentile(values, 0.95),
        "maximum": max(values),
    }


def metric_for_names(expected, names):
    present = [table for table in expected if table in names]
    missing = [table for table in expected if table not in names]
    return {
        "expected_tables_present": present,
        "missing_expected_tables": missing,
        "recall": len(present) / len(expected),
        "full_coverage": not missing,
        "has_any_expected_table": bool(present),
    }


def aggregate_case_metrics(rows, metric_key):
    recalls = [row[metric_key]["recall"] for row in rows]
    by_difficulty = defaultdict(list)
    by_domain = defaultdict(list)
    for row in rows:
        by_difficulty[str(row["difficulty"])].append(row[metric_key]["recall"])
        by_domain[str(row["domain"])].append(row[metric_key]["recall"])
    summarize = lambda values: {
        "question_count": len(values), "macro_candidate_recall": statistics.mean(values)
    }
    return {
        "question_count": len(rows),
        "macro_candidate_recall": statistics.mean(recalls),
        "full_coverage_count": sum(row[metric_key]["full_coverage"] for row in rows),
        "questions_with_at_least_one_expected_table": sum(
            row[metric_key]["has_any_expected_table"] for row in rows
        ),
        "expected_table_miss_occurrences": sum(
            len(row[metric_key]["missing_expected_tables"]) for row in rows
        ),
        "by_difficulty": {key: summarize(value) for key, value in sorted(by_difficulty.items())},
        "by_domain": {key: summarize(value) for key, value in sorted(by_domain.items())},
    }


def transitions(rows, depth):
    groups = {"improved": [], "unchanged": [], "regressed": []}
    key_original = f"original_at_{depth}"
    key_business = f"business_at_{depth}"
    for row in rows:
        old = row[key_original]["recall"]
        new = row[key_business]["recall"]
        group = "improved" if new > old else "regressed" if new < old else "unchanged"
        groups[group].append({"id": row["id"], "original": old, "business": new, "delta": new - old})
    return groups


def pool_summary(case_rows, pool_key):
    counts = [row[pool_key]["candidate_count"] for row in case_rows]
    recalls = [row[pool_key]["recall"] for row in case_rows]
    return {
        "question_count": len(case_rows),
        "total_question_table_pairs": sum(counts),
        "candidate_count": {
            "mean": statistics.mean(counts), "median": statistics.median(counts),
            "minimum": min(counts), "maximum": max(counts),
        },
        "macro_candidate_recall": statistics.mean(recalls),
        "full_coverage_count": sum(row[pool_key]["full_coverage"] for row in case_rows),
        "remaining_expected_table_miss_occurrences": sum(
            len(row[pool_key]["missing_expected_tables"]) for row in case_rows
        ),
        "capacity_adjusted_oracle_at_10": statistics.mean(
            min(10, len(row[pool_key]["expected_tables_present"])) / len(row["expected_tables"])
            for row in case_rows
        ),
    }


def metadata_diagnostic(table, audit_by_table, representation_by_table):
    audit = audit_by_table[table]
    def available(included, omitted):
        return sorted(set([*included, *omitted]), key=lambda value: (value.casefold(), value))
    all_columns = [*audit["included_columns"], *audit["omitted_columns"]]
    available_columns = [{
        "physical_column_name": item["physical_column_name"],
        "english_captions": available(item["included_captions"], item["omitted_captions"]),
    } for item in all_columns]
    present_columns = [{
        "physical_column_name": item["physical_column_name"],
        "english_captions": item["included_captions"],
    } for item in audit["included_columns"]]
    return {
        "available_english_metadata": {
            "table_labels": available(audit["included_table_labels"], audit["omitted_table_labels"]),
            "form_labels": available(audit["included_form_labels"], audit["omitted_form_labels"]),
            "module_labels": available(audit["included_module_labels"], audit["omitted_module_labels"]),
            "columns": available_columns,
        },
        "metadata_present_in_frozen_representation": {
            "table_labels": audit["included_table_labels"],
            "form_labels": audit["included_form_labels"],
            "module_labels": audit["included_module_labels"],
            "columns": present_columns,
        },
        "omitted_column_count": len(audit["omitted_columns"]),
        "any_columns_omitted": bool(audit["omitted_columns"]),
        "representation_sha256": representation_by_table[table]["sha256"],
    }


def main() -> None:
    if OUTPUT_PATH.exists():
        raise RuntimeError("Frozen result already exists; refusing a second evaluation")
    protected_payload = json.loads(PROTECTED_PATH.read_text(encoding="utf-8"))
    before = protected_payload["sha256"]
    for relative, expected_hash in before.items():
        if sha256_file(ROOT / relative) != expected_hash:
            raise RuntimeError(f"STOP: protected artifact changed before evaluation: {relative}")
    build_report = json.loads(BUILD_REPORT_PATH.read_text(encoding="utf-8"))
    if not (
        build_report["vector_count"] == 2196
        and build_report["vector_dimension"] == 1024
        and build_report["vectors_finite"]
        and build_report["vectors_l2_normalized"]
        and build_report["documents_requiring_truncation"] == 0
    ):
        raise RuntimeError("STOP: business index build audit failed")
    candidates = json.loads(CANDIDATES_PATH.read_text(encoding="utf-8"))
    if (
        candidates["candidate_policy"]["bge_dense_depth"] != 50
        or candidates["candidate_policy"]["minilm_graph_output_depth"] != 50
    ):
        raise RuntimeError("STOP: frozen candidate source depths changed")
    representations = json.loads(REPRESENTATIONS_PATH.read_text(encoding="utf-8"))
    audits = json.loads(AUDIT_PATH.read_text(encoding="utf-8"))
    representation_by_table = {
        item["fully_qualified_table"]: item for item in representations["tables"]
    }
    audit_by_table = {item["fully_qualified_table"]: item for item in audits["tables"]}

    reranker_results = json.loads(RERANKER_RESULTS_PATH.read_text(encoding="utf-8"))
    frozen_failures = []
    for case in reranker_results["suites"]["real_world_observed_13"]["cases"]:
        for failure in case["miss_failures"]:
            if failure["classification"] == "A_candidate_generation_failure":
                frozen_failures.append({"case_id": case["id"], "expected_table": failure["table"]})
    if len(frozen_failures) != 22:
        raise RuntimeError(f"STOP: expected 22 frozen candidate failures, found {len(frozen_failures)}")

    retriever = BGEBusinessDenseRetriever()
    warm_vector, warm_latency = retriever.encode_query(
        "Nonbenchmark warm-up sentence for dense candidate retrieval."
    )
    if warm_vector.shape != (1, 1024):
        raise RuntimeError("Warm-up query vector invalid")
    process = psutil.Process()
    peak_rss = process.memory_info().rss
    query_latencies, original_search_latencies, business_search_latencies = [], [], []
    case_rows_by_suite = {}
    case_lookup = {}
    ordinal = 0
    for suite_name in SUITE_ORDER:
        rows = []
        for case in candidates["suites"][suite_name]["cases"]:
            ordinal += 1
            query_vector, query_seconds = retriever.encode_query(case["question"])
            query_latencies.append(query_seconds)
            if ordinal % 2:
                original_ranking, original_seconds = retriever.search("original", query_vector)
                business_ranking, business_seconds = retriever.search("business", query_vector)
                order = ["original", "business"]
            else:
                business_ranking, business_seconds = retriever.search("business", query_vector)
                original_ranking, original_seconds = retriever.search("original", query_vector)
                order = ["business", "original"]
            original_search_latencies.append(original_seconds)
            business_search_latencies.append(business_seconds)
            peak_rss = max(peak_rss, process.memory_info().rss)
            original_by_table = {item["table"]: item for item in original_ranking}
            business_by_table = {item["table"]: item for item in business_ranking}
            expected_diagnostics = []
            for table in case["expected_tables"]:
                old = original_by_table[table]
                new = business_by_table[table]
                expected_diagnostics.append({
                    "table": table,
                    "original_bge_dense": {
                        "full_rank": old["rank"], "raw_cosine": old["raw_cosine"],
                        "cutoff_membership": {str(k): old["rank"] <= k for k in DEPTHS},
                    },
                    "bge_business_dense": {
                        "full_rank": new["rank"], "raw_cosine": new["raw_cosine"],
                        "cutoff_membership": {str(k): new["rank"] <= k for k in DEPTHS},
                    },
                    "rank_change_business_minus_original": new["rank"] - old["rank"],
                    "metadata": metadata_diagnostic(
                        table, audit_by_table, representation_by_table
                    ),
                    "cosine_comparison_warning": (
                        "Cross-representation cosine magnitudes are not interpreted as intrinsically better."
                    ),
                })
            row = {
                "id": case["id"], "question": case["question"],
                "difficulty": case["difficulty"], "domain": case["domain"],
                "expected_tables": case["expected_tables"],
                "search_order": order,
                "query_encoding_seconds": query_seconds,
                "original_search_seconds": original_seconds,
                "business_search_seconds": business_seconds,
                "expected_table_diagnostics": expected_diagnostics,
                "complete_original_ranking": original_ranking,
                "complete_business_ranking": business_ranking,
            }
            for depth in DEPTHS:
                row[f"original_at_{depth}"] = metric_for_names(
                    case["expected_tables"], {item["table"] for item in original_ranking[:depth]}
                )
                row[f"business_at_{depth}"] = metric_for_names(
                    case["expected_tables"], {item["table"] for item in business_ranking[:depth]}
                )
            saved_original = [item["table"] for item in case["bge_dense_top_50"]]
            live_original = [item["table"] for item in original_ranking[:50]]
            if live_original != saved_original:
                raise RuntimeError(f"STOP: original BGE Top-50 changed for {case['id']}")
            graph = [item["table"] for item in case["minilm_graph_top_50_or_available"]]
            business = [item["table"] for item in business_ranking[:50]]
            pools = {
                "control_pool": (
                    ("original_bge_dense", saved_original), ("minilm_graph", graph),
                ),
                "pool_a_replacement": (
                    ("bge_business_dense", business), ("minilm_graph", graph),
                ),
                "pool_b_addition": (
                    ("bge_business_dense", business),
                    ("original_bge_dense", saved_original),
                    ("minilm_graph", graph),
                ),
            }
            for pool_name, named_sources in pools.items():
                members = sorted(set().union(*(set(source) for _, source in named_sources)))
                provenance = {
                    table: [name for name, source in named_sources if table in source]
                    for table in members
                }
                metric = metric_for_names(case["expected_tables"], set(members))
                row[pool_name] = {
                    "candidate_count": len(members), "candidates": members,
                    "source_provenance": provenance, **metric,
                }
            rows.append(row)
            case_lookup[(suite_name, case["id"])] = row
            print(f"Evaluated {ordinal}/42 questions", flush=True)
        case_rows_by_suite[suite_name] = rows

    # Reproduce the frozen control before reporting new pool results.
    for suite_name, rows in case_rows_by_suite.items():
        summary = pool_summary(rows, "control_pool")
        target_recall, target_full = CONTROL_TARGETS[suite_name]
        if (
            abs(summary["macro_candidate_recall"] - target_recall) > 1e-12
            or summary["full_coverage_count"] != target_full
        ):
            raise RuntimeError(f"STOP: control candidate coverage mismatch for {suite_name}")

    failure_diagnostics = []
    for frozen in frozen_failures:
        row = case_lookup[("real_world_observed_13", frozen["case_id"])]
        diagnostic = next(
            item for item in row["expected_table_diagnostics"]
            if item["table"] == frozen["expected_table"]
        )
        old_rank = diagnostic["original_bge_dense"]["full_rank"]
        new_rank = diagnostic["bge_business_dense"]["full_rank"]
        if new_rank < old_rank:
            interpretation = "consistent with business representation helping"
        elif new_rank > old_rank:
            interpretation = "regression"
        else:
            interpretation = "no observed help"
        failure_diagnostics.append({
            "case_id": frozen["case_id"], "expected_table": frozen["expected_table"],
            "original_bge_dense_rank": old_rank,
            "bge_business_dense_rank": new_rank,
            "cutoff_membership_changes": {
                str(depth): {
                    "original": old_rank <= depth, "business": new_rank <= depth,
                } for depth in DEPTHS
            },
            "metadata": diagnostic["metadata"],
            "pool_a_recovers": frozen["expected_table"] in row["pool_a_replacement"]["candidates"],
            "pool_b_recovers": frozen["expected_table"] in row["pool_b_addition"]["candidates"],
            "interpretation": interpretation,
        })

    suites_output = {}
    for suite_name, rows in case_rows_by_suite.items():
        depth_metrics = {}
        for depth in DEPTHS:
            depth_metrics[str(depth)] = {
                "original_bge_dense": aggregate_case_metrics(rows, f"original_at_{depth}"),
                "bge_business_dense": aggregate_case_metrics(rows, f"business_at_{depth}"),
                "transitions": transitions(rows, depth),
            }
        suites_output[suite_name] = {
            "depth_metrics": depth_metrics,
            "candidate_pools": {
                key: pool_summary(rows, key)
                for key in ("control_pool", "pool_a_replacement", "pool_b_addition")
            },
            "cases": rows,
        }

    control_expected = set()
    pool_a_expected = set()
    pool_b_unique = []
    replacement_losses = []
    additional_counts = []
    for suite_name, rows in case_rows_by_suite.items():
        for row in rows:
            for table in row["expected_tables"]:
                occurrence = (suite_name, row["id"], table)
                if table in row["control_pool"]["candidates"]:
                    control_expected.add(occurrence)
                if table in row["pool_a_replacement"]["candidates"]:
                    pool_a_expected.add(occurrence)
                if (
                    table in row["pool_b_addition"]["candidates"]
                    and table not in row["control_pool"]["candidates"]
                    and table in {item["table"] for item in row["complete_business_ranking"][:50]}
                ):
                    pool_b_unique.append({"suite": suite_name, "case_id": row["id"], "table": table})
            additional_counts.append(
                row["pool_b_addition"]["candidate_count"] - row["control_pool"]["candidate_count"]
            )
    for suite_name, case_id, table in sorted(control_expected - pool_a_expected):
        replacement_losses.append({"suite": suite_name, "case_id": case_id, "table": table})
    replacement_additions = [
        {"suite": suite, "case_id": case_id, "table": table}
        for suite, case_id, table in sorted(pool_a_expected - control_expected)
    ]

    after = {relative: sha256_file(ROOT / relative) for relative in before}
    if after != before:
        raise RuntimeError("STOP: protected artifact changed during evaluation")
    result = {
        "experiment": "BGE-Business-Dense",
        "primary_outcome": "observed real-world candidate Recall@50",
        "configuration": {
            "model": "BAAI/bge-m3", "revision": "5617a9f61b028005a4858fdac845db406aefb181",
            "dense_only": True, "dimension": 1024, "pooling": "cls",
            "device": "cpu", "precision": "float32", "batch_size": 1,
            "max_sequence_tokens": 8192, "normalized": True,
            "index": "faiss.IndexFlatIP", "candidate_depths": DEPTHS,
        },
        "build_report": build_report,
        "warmup": {"kind": "nonbenchmark", "query_encoding_seconds": warm_latency},
        "suites": suites_output,
        "frozen_real_world_candidate_failure_diagnostics": failure_diagnostics,
        "replacement_test": {
            "additional_expected_table_occurrences": replacement_additions,
            "lost_control_expected_table_occurrences": replacement_losses,
            "credible_replacement": bool(replacement_additions) and not replacement_losses,
        },
        "complementarity_test": {
            "expected_table_occurrences_uniquely_contributed_by_business_top_50": pool_b_unique,
            "additional_candidate_counts_per_question": additional_counts,
            "total_additional_question_table_pairs": sum(additional_counts),
            "mean_additional_candidates_per_question": statistics.mean(additional_counts),
        },
        "latency": {
            "model_load_seconds": retriever.model_load_seconds,
            "nonbenchmark_warmup_query_seconds": warm_latency,
            "query_encoding_seconds": timing_distribution(query_latencies),
            "original_index_search_seconds": timing_distribution(original_search_latencies),
            "business_index_search_seconds": timing_distribution(business_search_latencies),
            "original_combined_seconds": timing_distribution([
                query + search for query, search in zip(query_latencies, original_search_latencies)
            ]),
            "business_combined_seconds": timing_distribution([
                query + search for query, search in zip(query_latencies, business_search_latencies)
            ]),
            "peak_process_rss_bytes": peak_rss,
        },
        "integrity": {
            "protected_hashes_unchanged_before_and_after": True,
            "representation_sha256": sha256_file(REPRESENTATIONS_PATH),
            "business_vectors": build_report["vector_count"],
            "business_vector_dimension": build_report["vector_dimension"],
            "vectors_finite": build_report["vectors_finite"],
            "vectors_l2_normalized": build_report["vectors_l2_normalized"],
            "representation_truncation_count": build_report["documents_requiring_truncation"],
            "candidate_source_depths": {"dense": 50, "graph": 50},
            "query_encoded_once_per_benchmark_question": True,
            "shared_query_vector_for_both_indexes": True,
            "manual_mappings": False, "reranking": False, "database_accessed": False,
            "sql_executed": False, "qwen_run": False, "support_tickets_accessed": False,
            "unseen_benchmark_inspected": False, "post_result_tuning": False,
        },
    }
    OUTPUT_PATH.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "event": "BGE-Business-Dense evaluation complete",
        "primary": suites_output["real_world_observed_13"]["depth_metrics"]["50"],
        "replacement_test": result["replacement_test"],
        "complementarity_test": result["complementarity_test"],
        "latency": result["latency"],
    }, ensure_ascii=False, indent=2), flush=True)


if __name__ == "__main__":
    main()
