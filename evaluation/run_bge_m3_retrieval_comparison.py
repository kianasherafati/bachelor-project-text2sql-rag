"""Execute the single frozen MiniLM-versus-BGE-M3 retrieval comparison."""

from __future__ import annotations

from collections import defaultdict
import hashlib
import json
import math
import os
from pathlib import Path
import statistics
import sys
import time


ROOT = Path(__file__).resolve().parents[1]
EVALUATION_DIR = ROOT / "evaluation"
RETRIEVAL_DIR = ROOT / "retrieval"
RESULT_PATH = EVALUATION_DIR / "bge_m3_retrieval_comparison_results.json"
COVERAGE_PATH = EVALUATION_DIR / "bge_m3_document_coverage.json"
HASHES_PATH = EVALUATION_DIR / "bge_m3_protected_hashes_before.json"
BUILD_REPORT_PATH = RETRIEVAL_DIR / "bge_m3_schema_build_report.json"
MANIFEST_PATH = RETRIEVAL_DIR / "bge_m3_model_manifest.json"
sys.path.insert(0, str(EVALUATION_DIR))
sys.path.insert(0, str(RETRIEVAL_DIR))
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
os.environ.setdefault("OMP_NUM_THREADS", "8")
os.environ.setdefault("MKL_NUM_THREADS", "8")

from bge_m3_retriever import BGEM3SchemaRetriever
from erp_retrieval_benchmark import tests as development_tests
from erp_retrieval_heldout_benchmark import tests as heldout_tests
from graph_expanded_retriever import FIXED_FK_BONUS, GraphExpandedSchemaRetriever
from hybrid_retriever import DENSE_WEIGHT, LEXICAL_WEIGHT
from real_world_text2sql_benchmark import tests as real_world_tests


TOP_K = 10
SYSTEMS = (
    "MiniLM Dense", "BGE-Dense", "MiniLM Hybrid", "BGE-Hybrid",
    "MiniLM Graph", "BGE-Graph",
)
TRANSITIONS = (
    ("MiniLM Dense", "BGE-Dense"),
    ("MiniLM Hybrid", "BGE-Hybrid"),
    ("MiniLM Graph", "BGE-Graph"),
)
FROZEN_BASELINES = {
    "development_9": {
        "MiniLM Dense": 0.4259, "MiniLM Hybrid": 0.6296, "MiniLM Graph": 0.9444,
    },
    "heldout_schema_20": {
        "MiniLM Dense": 0.5458, "MiniLM Hybrid": 0.7208, "MiniLM Graph": 0.8875,
    },
    "real_world_observed_13": {
        "MiniLM Dense": 0.0769, "MiniLM Hybrid": 0.2692, "MiniLM Graph": 0.3654,
    },
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def suites():
    development = []
    for index, case in enumerate(development_tests, start=1):
        item = dict(case)
        item["id"] = f"DEV-{index:02d}"
        item.setdefault("domain", None)
        development.append(item)
    return {
        "development_9": development,
        "heldout_schema_20": [dict(case) for case in heldout_tests],
        "real_world_observed_13": [dict(case) for case in real_world_tests],
    }


def verify_protected_hashes():
    frozen = json.loads(HASHES_PATH.read_text(encoding="utf-8"))["sha256"]
    current = {
        relative: sha256_file(ROOT / relative)
        for relative in frozen
    }
    if current != frozen:
        changed = sorted(key for key in frozen if current.get(key) != frozen[key])
        raise ValueError(f"Protected files changed: {changed}")
    return frozen


def normalized_dense(raw):
    return max(0.0, min(1.0, (float(raw) + 1.0) / 2.0))


def rank_map(results):
    return {
        result["full_name"]: (rank, result)
        for rank, result in enumerate(results, start=1)
    }


def raw_cosine(system, result):
    if result is None:
        return None
    if system.startswith("BGE"):
        return result.get("raw_bge_cosine", result.get("score"))
    if system == "MiniLM Dense":
        return result["score"]
    return 2.0 * result["dense_score"] - 1.0


def normalized_score(system, result):
    if result is None:
        return None
    if system.endswith("Dense"):
        return normalized_dense(raw_cosine(system, result))
    return result["dense_score"]


def final_score(system, result):
    if result is None:
        return None
    if system.endswith("Dense"):
        return raw_cosine(system, result)
    if system.endswith("Hybrid"):
        return result["combined_score"]
    return result["final_score"]


def compact_result(system, rank, result):
    item = {
        "rank": rank,
        "table": result["full_name"],
        "raw_cosine": raw_cosine(system, result),
        "normalized_dense_score": normalized_score(system, result),
    }
    if not system.endswith("Dense"):
        item.update({
            "lexical_score": result["lexical_score"],
            "hybrid_score": result.get("combined_score", result.get("hybrid_score")),
        })
    if system.endswith("Graph"):
        item.update({
            "graph_signal": result["graph_signal"],
            "fk_bonus_contribution": result["fk_bonus_contribution"],
            "final_score": result["final_score"],
            "is_hybrid_seed": result["is_hybrid_seed"],
            "source_seed_tables": result["source_seed_tables"],
        })
    return item


def evaluate_case(case, system, results):
    top = results[:TOP_K]
    if len(top) != TOP_K or len({row["full_name"] for row in top}) != TOP_K:
        raise ValueError(f"{case['id']} {system} did not produce 10 distinct results")
    expected = list(case["expected_tables"])
    retrieved = {row["full_name"] for row in top}
    missing = [name for name in expected if name not in retrieved]
    hits = len(expected) - len(missing)
    return {
        "id": case["id"],
        "question": case["question"],
        "difficulty": case.get("difficulty"),
        "domain": case.get("domain"),
        "expected_tables": expected,
        "retrieved_top_10": [
            compact_result(system, rank, result)
            for rank, result in enumerate(top, start=1)
        ],
        "missing_expected_tables": missing,
        "expected_tables_retrieved": hits,
        "recall_at_10": hits / len(expected),
        "full_coverage": hits == len(expected),
    }


def aggregate(rows, field=None):
    grouped = defaultdict(list)
    for row in rows:
        key = row.get(field) if field else "overall"
        if key is not None:
            grouped[key].append(row)
    return {
        key: {
            "question_count": len(group),
            "macro_recall_at_10": statistics.mean(
                item["recall_at_10"] for item in group
            ),
            "full_coverage_count": sum(item["full_coverage"] for item in group),
        }
        for key, group in sorted(grouped.items())
    }


def stats(values):
    if not values:
        return None
    return {
        "count": len(values),
        "mean": statistics.mean(values),
        "median": statistics.median(values),
        "standard_deviation": statistics.pstdev(values),
        "minimum": min(values),
        "maximum": max(values),
    }


def expected_diagnostics(case, full_rankings):
    output = []
    maps = {system: rank_map(full_rankings[system]) for system in SYSTEMS}
    for table in case["expected_tables"]:
        item = {"expected_table": table}
        for system in SYSTEMS:
            rank, result = maps[system].get(table, (None, None))
            details = {
                "rank": rank,
                "raw_cosine": raw_cosine(system, result),
                "normalized_dense_score": normalized_score(system, result),
                "lexical_score": (
                    result.get("lexical_score") if result is not None else None
                ),
                "hybrid_score": (
                    result.get("combined_score", result.get("hybrid_score"))
                    if result is not None else None
                ),
                "graph_candidate": result is not None if system.endswith("Graph") else None,
                "graph_signal": (
                    result.get("graph_signal") if result is not None else None
                ),
                "fk_bonus_contribution": (
                    result.get("fk_bonus_contribution") if result is not None else None
                ),
                "final_score": final_score(system, result),
            }
            item[system] = details
        output.append(item)
    return output


def transition(cases, old_system, new_system, evaluations, full_rankings):
    old_rows = {row["id"]: row for row in evaluations[old_system]}
    new_rows = {row["id"]: row for row in evaluations[new_system]}
    groups = {"improved": [], "unchanged": [], "regressed": []}
    evidence = []
    for case in cases:
        case_id = case["id"]
        old_row, new_row = old_rows[case_id], new_rows[case_id]
        if new_row["recall_at_10"] > old_row["recall_at_10"]:
            classification = "improved"
        elif new_row["recall_at_10"] < old_row["recall_at_10"]:
            classification = "regressed"
        else:
            classification = "unchanged"
        groups[classification].append(case_id)
        old_top = {row["table"] for row in old_row["retrieved_top_10"]}
        new_top = {row["table"] for row in new_row["retrieved_top_10"]}
        old_map = rank_map(full_rankings[case_id][old_system])
        new_map = rank_map(full_rankings[case_id][new_system])
        changes = []
        for status, names in (
            ("gained", [name for name in case["expected_tables"] if name not in old_top and name in new_top]),
            ("lost", [name for name in case["expected_tables"] if name in old_top and name not in new_top]),
        ):
            for name in names:
                old_rank, old_result = old_map.get(name, (None, None))
                new_rank, new_result = new_map.get(name, (None, None))
                changes.append({
                    "status": status,
                    "expected_table": name,
                    "old_rank": old_rank,
                    "new_rank": new_rank,
                    "minilm_cosine": raw_cosine(old_system, old_result),
                    "bge_cosine": raw_cosine(new_system, new_result),
                    "old_normalized_dense_score": normalized_score(old_system, old_result),
                    "new_normalized_dense_score": normalized_score(new_system, new_result),
                    "lexical_score": (
                        new_result.get("lexical_score") if new_result else
                        old_result.get("lexical_score") if old_result else None
                    ),
                    "old_hybrid_score": (
                        old_result.get("combined_score", old_result.get("hybrid_score"))
                        if old_result else None
                    ),
                    "new_hybrid_score": (
                        new_result.get("combined_score", new_result.get("hybrid_score"))
                        if new_result else None
                    ),
                    "old_graph_candidate": old_result is not None if old_system.endswith("Graph") else None,
                    "new_graph_candidate": new_result is not None if new_system.endswith("Graph") else None,
                    "old_graph_contribution": old_result.get("fk_bonus_contribution") if old_result else None,
                    "new_graph_contribution": new_result.get("fk_bonus_contribution") if new_result else None,
                    "old_final_rank": old_rank,
                    "new_final_rank": new_rank,
                })
        evidence.append({
            "case_id": case_id,
            "classification": classification,
            "old_recall_at_10": old_row["recall_at_10"],
            "new_recall_at_10": new_row["recall_at_10"],
            "expected_table_changes": changes,
        })
    return {**groups, "per_case_evidence": evidence}


def score_distributions(cases, full_rankings):
    output = {}
    for system in ("MiniLM Dense", "BGE-Dense"):
        raw, normalized, expected, spreads = [], [], [], []
        for case in cases:
            results = full_rankings[case["id"]][system]
            raw_values = [raw_cosine(system, row) for row in results]
            raw.extend(raw_values)
            normalized.extend(normalized_dense(value) for value in raw_values)
            spreads.append(raw_values[0] - raw_values[TOP_K - 1])
            lookup = rank_map(results)
            expected.extend(
                raw_cosine(system, lookup[name][1]) for name in case["expected_tables"]
            )
        output[system] = {
            "raw_cosine": stats(raw),
            "normalized_dense_score": stats(normalized),
            "top_10_raw_score_spread_per_query": stats(spreads),
            "expected_table_raw_cosine": stats(expected),
        }
    return output


def latency_summary(latencies):
    return {
        system: {
            "query_count": len(values),
            "mean_seconds": statistics.mean(values),
            "median_seconds": statistics.median(values),
            "maximum_seconds": max(values),
        }
        for system, values in latencies.items()
    }


def late_field_analysis(coverage, all_full_rankings, suite_cases):
    output = []
    for field in coverage["frozen_late_field_coverage"]:
        table = field["table"]
        cases = []
        for suite_name, definitions in suite_cases.items():
            for case in definitions:
                if table not in case["expected_tables"]:
                    continue
                rankings = all_full_rankings[suite_name][case["id"]]
                mini_dense = rank_map(rankings["MiniLM Dense"])[table][0]
                bge_dense = rank_map(rankings["BGE-Dense"])[table][0]
                mini_graph = rank_map(rankings["MiniLM Graph"]).get(table, (None, None))[0]
                bge_graph = rank_map(rankings["BGE-Graph"]).get(table, (None, None))[0]
                cases.append({
                    "suite": suite_name,
                    "case_id": case["id"],
                    "minilm_dense_rank": mini_dense,
                    "bge_dense_rank": bge_dense,
                    "dense_rank_improved": bge_dense < mini_dense,
                    "minilm_graph_rank": mini_graph,
                    "bge_graph_rank": bge_graph,
                    "bge_dense_top_10_gain": mini_dense > TOP_K and bge_dense <= TOP_K,
                    "bge_graph_top_10_gain": (
                        (mini_graph is None or mini_graph > TOP_K)
                        and bge_graph is not None and bge_graph <= TOP_K
                    ),
                })
        output.append({**field, "benchmark_cases_where_table_is_expected": cases})
    return output


def opaque_analysis(coverage, real_cases, real_rankings):
    by_id = {case["id"]: case for case in real_cases}
    output = []
    for diagnostic in coverage["frozen_opaque_identifier_diagnostics"]:
        case_id = diagnostic["case_id"]
        tables = diagnostic["physical_tables"] or by_id[case_id]["expected_tables"]
        rankings = real_rankings[case_id]
        mini = rank_map(rankings["MiniLM Dense"])
        bge = rank_map(rankings["BGE-Dense"])
        output.append({
            **diagnostic,
            "physical_tables": list(tables),
            "dense_rank_movements": [
                {
                    "table": table,
                    "minilm_dense_rank": mini[table][0],
                    "bge_dense_rank": bge[table][0],
                    "rank_change_positive_means_improvement": mini[table][0] - bge[table][0],
                }
                for table in tables
            ],
        })
    return output


def real_world_business_language_analysis(real_cases, real_rankings):
    output = []
    for case in real_cases:
        mini = rank_map(real_rankings[case["id"]]["MiniLM Dense"])
        bge = rank_map(real_rankings[case["id"]]["BGE-Dense"])
        output.append({
            "case_id": case["id"],
            "expected_table_dense_rank_movements": [
                {
                    "table": table,
                    "minilm_rank": mini[table][0],
                    "bge_rank": bge[table][0],
                    "rank_change_positive_means_improvement": mini[table][0] - bge[table][0],
                }
                for table in case["expected_tables"]
            ],
        })
    return output


def timed(callable_):
    started = time.perf_counter()
    result = callable_()
    return result, time.perf_counter() - started


def main():
    protected_before = verify_protected_hashes()
    suite_cases = suites()
    if {name: len(items) for name, items in suite_cases.items()} != {
        "development_9": 9, "heldout_schema_20": 20,
        "real_world_observed_13": 13,
    }:
        raise ValueError("Benchmark suite sizes changed")
    coverage = json.loads(COVERAGE_PATH.read_text(encoding="utf-8"))
    build_report = json.loads(BUILD_REPORT_PATH.read_text(encoding="utf-8"))
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    if coverage["status"] != "frozen_before_benchmark_retrieval_evaluation":
        raise ValueError("Coverage artifact was not frozen pre-result")

    mini = GraphExpandedSchemaRetriever()
    bge = BGEM3SchemaRetriever()
    mini.embedding_model.encode(
        ["Nonbenchmark warm-up sentence for dense retrieval."],
        convert_to_numpy=True,
        normalize_embeddings=True,
    )
    bge.warmup()

    evaluations_by_suite = {}
    rankings_by_suite = {}
    expected_by_suite = {}
    transitions_by_suite = {}
    distributions_by_suite = {}
    latencies = {system: [] for system in SYSTEMS}

    for suite_name, cases in suite_cases.items():
        evaluations = {system: [] for system in SYSTEMS}
        suite_rankings = {}
        suite_expected = {}
        for case in cases:
            n = len(mini.documents)
            runs = {}
            runs["MiniLM Dense"], elapsed = timed(
                lambda: mini.retrieve(case["question"], top_k=n)
            )
            latencies["MiniLM Dense"].append(elapsed)
            runs["BGE-Dense"], elapsed = timed(
                lambda: bge.retrieve_bge_dense(case["question"], top_k=n)
            )
            latencies["BGE-Dense"].append(elapsed)
            runs["MiniLM Hybrid"], elapsed = timed(
                lambda: mini.retrieve_hybrid(case["question"], top_k=n)
            )
            latencies["MiniLM Hybrid"].append(elapsed)
            runs["BGE-Hybrid"], elapsed = timed(
                lambda: bge.retrieve_bge_hybrid(case["question"], top_k=n)
            )
            latencies["BGE-Hybrid"].append(elapsed)
            mini_graph, elapsed = timed(
                lambda: mini.retrieve_graph_expanded(case["question"], top_k=n)
            )
            runs["MiniLM Graph"] = mini_graph["results"]
            latencies["MiniLM Graph"].append(elapsed)
            bge_graph, elapsed = timed(
                lambda: bge.retrieve_bge_graph(case["question"], top_k=n)
            )
            runs["BGE-Graph"] = bge_graph["results"]
            latencies["BGE-Graph"].append(elapsed)

            mini_lexical = {
                row["full_name"]: row["lexical_score"]
                for row in runs["MiniLM Hybrid"]
            }
            bge_lexical = {
                row["full_name"]: row["lexical_score"]
                for row in runs["BGE-Hybrid"]
            }
            if mini_lexical != bge_lexical:
                raise ValueError(f"Lexical scores changed for {case['id']}")
            suite_rankings[case["id"]] = runs
            suite_expected[case["id"]] = expected_diagnostics(case, runs)
            for system in SYSTEMS:
                evaluations[system].append(
                    evaluate_case(case, system, runs[system])
                )
            print(f"Evaluated {suite_name} {case['id']}", flush=True)

        aggregates = {}
        for system in SYSTEMS:
            rows = evaluations[system]
            overall = aggregate(rows)["overall"]
            eligible = [row for row in rows if row["id"] != "REAL-C04"]
            aggregates[system] = {
                **overall,
                "full_coverage_among_top10_eligible": sum(
                    row["full_coverage"] for row in eligible
                ),
                "top10_eligible_denominator": len(eligible),
                "by_difficulty": aggregate(rows, "difficulty"),
                "by_domain": aggregate(rows, "domain"),
            }
        for system, historical in FROZEN_BASELINES[suite_name].items():
            reproduced = aggregates[system]["macro_recall_at_10"]
            if round(reproduced, 4) != historical:
                raise ValueError(
                    f"Frozen baseline mismatch {suite_name} {system}: "
                    f"{reproduced:.4f} != {historical:.4f}"
                )
        evaluations_by_suite[suite_name] = {
            "per_system": evaluations,
            "aggregates": aggregates,
        }
        rankings_by_suite[suite_name] = suite_rankings
        expected_by_suite[suite_name] = suite_expected
        transitions_by_suite[suite_name] = {
            f"{old} -> {new}": transition(
                cases, old, new, evaluations, suite_rankings
            )
            for old, new in TRANSITIONS
        }
        distributions_by_suite[suite_name] = score_distributions(
            cases, suite_rankings
        )

    real_case = next(
        case for case in suite_cases["real_world_observed_13"]
        if case["id"] == "REAL-C04"
    )
    real_evaluations = evaluations_by_suite["real_world_observed_13"]["per_system"]
    c04 = {}
    for system in SYSTEMS:
        row = next(item for item in real_evaluations[system] if item["id"] == "REAL-C04")
        c04[system] = {
            "expected_table_count": len(real_case["expected_tables"]),
            "retrieved_expected_table_count": row["expected_tables_retrieved"],
            "recall_at_10": row["recall_at_10"],
            "theoretical_ceiling": 10 / 12,
            "ceiling_reached": row["expected_tables_retrieved"] == 10,
            "missing_expected_tables": row["missing_expected_tables"],
        }

    after = verify_protected_hashes()
    if after != protected_before:
        raise ValueError("Protected hashes changed during evaluation")
    result = {
        "experiment": "frozen_bge_m3_dense_long_context",
        "execution_policy": {
            "single_frozen_run": True,
            "top_k": TOP_K,
            "cpu_threads": {
                "OMP_NUM_THREADS": os.environ.get("OMP_NUM_THREADS"),
                "MKL_NUM_THREADS": os.environ.get("MKL_NUM_THREADS"),
            },
            "no_cross_mode_result_caching": True,
            "real_world_suite_status": "observed development/stress suite",
        },
        "model_manifest_sha256": sha256_file(MANIFEST_PATH),
        "coverage_sha256": sha256_file(COVERAGE_PATH),
        "build_report": build_report,
        "suites": evaluations_by_suite,
        "full_expected_table_diagnostics": expected_by_suite,
        "transitions": transitions_by_suite,
        "score_distributions": distributions_by_suite,
        "late_field_coverage_analysis": late_field_analysis(
            coverage, rankings_by_suite, suite_cases
        ),
        "business_language_analysis": real_world_business_language_analysis(
            suite_cases["real_world_observed_13"],
            rankings_by_suite["real_world_observed_13"],
        ),
        "opaque_identifier_analysis": opaque_analysis(
            coverage,
            suite_cases["real_world_observed_13"],
            rankings_by_suite["real_world_observed_13"],
        ),
        "real_c04": c04,
        "latency": {
            "model_load_seconds": {
                "BGE_build_process": build_report["model_load_seconds"],
                "BGE_evaluation_process": bge.model_load_seconds,
            },
            "query_latency": latency_summary(latencies),
            "comparability_note": (
                "Each mode encoded each exact question independently after one "
                "nonbenchmark warm-up; full rankings were retained from that run."
            ),
        },
        "integrity": {
            "protected_files_unchanged": True,
            "protected_hash_count": len(after),
            "documents": build_report["document_count"],
            "vectors": build_report["vector_count"],
            "one_vector_per_table": build_report["vector_count"] == 2196,
            "dimension_1024": build_report["vector_dimension"] == 1024,
            "vectors_finite": build_report["all_vectors_finite"],
            "vectors_l2_normalized": build_report["all_vectors_l2_normalized"],
            "max_encoded_length_at_most_8192": (
                build_report["maximum_observed_encoded_tokens"] <= 8192
            ),
            "model_revision_matches_manifest": (
                manifest["resolved_model_revision"]
                == "5617a9f61b028005a4858fdac845db406aefb181"
            ),
            "lexical_scores_exactly_reproduced": True,
            "hybrid_weights": {
                "dense": DENSE_WEIGHT, "lexical": LEXICAL_WEIGHT,
            },
            "fk_bonus": FIXED_FK_BONUS,
            "graph_hops": 1,
            "graph_direction": "outgoing",
            "aliases_used": False,
            "bm25_used": False,
            "chunked_representation_used": False,
            "reranking_used": False,
            "database_accessed": False,
            "sql_executed": False,
            "qwen_run": False,
            "unseen_ticket_benchmark_inspected": False,
            "post_result_tuning": False,
        },
    }
    RESULT_PATH.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        suite: {
            system: round(data["aggregates"][system]["macro_recall_at_10"], 4)
            for system in SYSTEMS
        }
        for suite, data in evaluations_by_suite.items()
    }, indent=2))


if __name__ == "__main__":
    main()
