"""Run the frozen bounded reverse-FK/form-association graph experiment once."""

from __future__ import annotations

from collections import defaultdict
import hashlib
import json
import math
from pathlib import Path
import statistics
import sys
import time


ROOT = Path(__file__).resolve().parents[1]
RETRIEVAL = ROOT / "retrieval"
sys.path.insert(0, str(RETRIEVAL))

from augmented_graph_retriever import (  # noqa: E402
    ADDITIONAL_NEIGHBOR_CAP,
    AugmentedGraphSchemaRetriever,
)
from graph_expanded_retriever import FIXED_FK_BONUS, HYBRID_SEED_COUNT  # noqa: E402


GRAPH_PATH = RETRIEVAL / "augmented_relationship_graph.json"
CANDIDATES_PATH = ROOT / "evaluation" / "bge_reranker_candidate_lists.json"
RERANKER_RESULTS_PATH = ROOT / "evaluation" / "bge_reranker_comparison_results.json"
PROTECTED_PATH = ROOT / "evaluation" / "augmented_graph_protected_hashes_before.json"
OUTPUT_PATH = ROOT / "evaluation" / "augmented_graph_comparison_results.json"
SUITES = ["development_9", "heldout_schema_20", "real_world_observed_13"]
CONTROL_TOP10_TARGETS = {
    "development_9": 0.9444444444444444,
    "heldout_schema_20": 0.8875,
    "real_world_observed_13": 0.36538461538461536,
}


def sha256_file(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def protected_paths():
    explicit = [
        "retrieval/schema.index",
        "retrieval/schema_metadata.pkl",
        "schema_extraction/schema.json",
        "schema_extraction/schema_documents.json",
        "retrieval/retriever.py",
        "retrieval/hybrid_retriever.py",
        "retrieval/graph_expanded_retriever.py",
        "retrieval/business_alias_source.json",
        "retrieval/business_alias_catalog.json",
        "retrieval/erp_retrieval_benchmark.py",
        "retrieval/erp_retrieval_heldout_benchmark.py",
        "evaluation/real_world_text2sql_benchmark.py",
        "evaluation/text2sql_gold_benchmark.py",
        "evaluation/real_world_gold_benchmark.py",
        "evaluation/bge_reranker_candidate_lists.json",
        "evaluation/bge_reranker_comparison_results.json",
        "retrieval/bge_m3_schema.index",
        "retrieval/bge_m3_schema_metadata.json",
        "retrieval/bge_m3_model_manifest.json",
        "retrieval/bge_m3_schema_build_report.json",
        "retrieval/bge_business_schema.index",
        "retrieval/bge_business_schema_metadata.json",
        "retrieval/bge_business_schema_build_report.json",
        "retrieval/bge_reranker_table_representations.json",
        "retrieval/bge_reranker_representation_audit.json",
        "retrieval/bge_reranker_representation_build_report.json",
        "retrieval/bge_reranker_v2_m3_manifest.json",
        "retrieval/bge_reranker_v2_m3.py",
        "evaluation/text2sql_gold_validation.json",
        "evaluation/real_world_gold_validation.json",
    ]
    found = []
    for relative in explicit:
        path = ROOT / relative
        if path.is_file():
            found.append(path)
    return found


def metric(expected, names):
    present = [table for table in expected if table in names]
    missing = [table for table in expected if table not in names]
    return {
        "expected_tables_present": present,
        "missing_expected_tables": missing,
        "recall": len(present) / len(expected),
        "full_coverage": not missing,
    }


def compact_result(result, rank):
    return {
        "rank": rank,
        "table": result["full_name"],
        "dense_score": result["dense_score"],
        "lexical_score": result["lexical_score"],
        "hybrid_score": result["hybrid_score"],
        "graph_signal": result["graph_signal"],
        "fk_bonus_contribution": result["fk_bonus_contribution"],
        "final_score": result["final_score"],
        "is_hybrid_seed": result["is_hybrid_seed"],
        "source_seed_tables": result["source_seed_tables"],
        "best_source_seed_rank": result["best_source_seed_rank"],
        "best_source_seed_hybrid_score": result["best_source_seed_hybrid_score"],
        "best_source_edge_families": result.get("best_source_edge_families", []),
        "source_edges": result.get("source_edges", []),
    }


def aggregate(rows, metric_key):
    recalls = [row[metric_key]["recall"] for row in rows]
    by_difficulty = defaultdict(list)
    by_domain = defaultdict(list)
    for row in rows:
        by_difficulty[str(row["difficulty"])].append(row[metric_key]["recall"])
        by_domain[str(row["domain"])].append(row[metric_key]["recall"])
    summarize = lambda values: {
        "question_count": len(values), "macro_recall": statistics.mean(values)
    }
    return {
        "question_count": len(rows),
        "macro_recall": statistics.mean(recalls),
        "full_coverage_count": sum(row[metric_key]["full_coverage"] for row in rows),
        "expected_table_miss_occurrences": sum(
            len(row[metric_key]["missing_expected_tables"]) for row in rows
        ),
        "by_difficulty": {
            key: summarize(value) for key, value in sorted(by_difficulty.items())
        },
        "by_domain": {key: summarize(value) for key, value in sorted(by_domain.items())},
    }


def pool_summary(rows, key):
    counts = [row[key]["candidate_count"] for row in rows]
    return {
        "question_count": len(rows),
        "candidate_count": {
            "mean": statistics.mean(counts),
            "median": statistics.median(counts),
            "minimum": min(counts),
            "maximum": max(counts),
        },
        "macro_candidate_recall": statistics.mean(row[key]["recall"] for row in rows),
        "full_coverage_count": sum(row[key]["full_coverage"] for row in rows),
        "expected_table_miss_occurrences": sum(
            len(row[key]["missing_expected_tables"]) for row in rows
        ),
        "capacity_adjusted_oracle_at_10": statistics.mean(
            min(10, len(row[key]["expected_tables_present"])) / len(row["expected_tables"])
            for row in rows
        ),
    }


def timing_summary(values):
    return {
        "mean": statistics.mean(values),
        "median": statistics.median(values),
        "minimum": min(values),
        "maximum": max(values),
    }


def deep_size(value, seen=None):
    """Approximate retained Python-object memory without third-party tooling."""
    if seen is None:
        seen = set()
    identity = id(value)
    if identity in seen:
        return 0
    seen.add(identity)
    size = sys.getsizeof(value)
    if isinstance(value, dict):
        return size + sum(
            deep_size(key, seen) + deep_size(item, seen) for key, item in value.items()
        )
    if isinstance(value, (list, tuple, set, frozenset)):
        return size + sum(deep_size(item, seen) for item in value)
    return size


def transitions(rows, old_key, new_key):
    groups = {"improved": [], "unchanged": [], "regressed": []}
    for row in rows:
        old = row[old_key]["recall"]
        new = row[new_key]["recall"]
        label = "improved" if new > old else "regressed" if new < old else "unchanged"
        groups[label].append({
            "id": row["id"], "control": old, "augmented": new, "delta": new - old
        })
    return groups


def main():
    if OUTPUT_PATH.exists() or PROTECTED_PATH.exists():
        raise RuntimeError("Frozen augmented-graph evaluation already started; refusing rerun")
    graph = json.loads(GRAPH_PATH.read_text(encoding="utf-8"))
    validation = graph["structural_validation"]
    if not validation["all_expected_measurements_match"]:
        raise RuntimeError("STOP: structural graph validation did not pass")
    if not (
        validation["outgoing_directed_pairs"] == 4369
        and validation["bidirectional_physical_directed_pairs"] == 8738
        and validation["form_association_directed_pairs"] == 1228
        and validation["novel_form_association_directed_pairs"] == 10
        and validation["combined_directed_pairs"] == 8748
    ):
        raise RuntimeError("STOP: frozen graph counts changed")
    allowed_families = {
        "outgoing_physical_fk", "reverse_physical_fk", "explicit_form_association"
    }
    for edge in graph["edges"]:
        if edge["source"] == edge["target"]:
            raise RuntimeError("STOP: graph contains a self edge")
        families = set(edge["supporting_edge_families"])
        if not families or not families <= allowed_families:
            raise RuntimeError("STOP: graph contains an unsupported edge family")
        if families != {item["family"] for item in edge["provenance"]}:
            raise RuntimeError("STOP: graph edge family lacks matching provenance")

    protected = {
        str(path.relative_to(ROOT)).replace("\\", "/"): sha256_file(path)
        for path in protected_paths()
    }
    protected_payload = {
        "created_before_benchmark_loading": True,
        "augmented_graph_sha256": sha256_file(GRAPH_PATH),
        "sha256": protected,
    }
    PROTECTED_PATH.write_text(
        json.dumps(protected_payload, indent=2) + "\n", encoding="utf-8"
    )

    # Benchmark questions and expected tables are loaded only after graph freezing.
    frozen_candidates = json.loads(CANDIDATES_PATH.read_text(encoding="utf-8"))
    if [len(frozen_candidates["suites"][name]["cases"]) for name in SUITES] != [9, 20, 13]:
        raise RuntimeError("STOP: benchmark suite sizes changed")

    retriever = AugmentedGraphSchemaRetriever()
    if HYBRID_SEED_COUNT != 10 or ADDITIONAL_NEIGHBOR_CAP != 10 or FIXED_FK_BONUS != 0.20:
        raise RuntimeError("STOP: frozen retrieval constants changed")

    all_rows = {}
    timings = defaultdict(list)
    for suite_name in SUITES:
        rows = []
        for ordinal, case in enumerate(frozen_candidates["suites"][suite_name]["cases"], 1):
            query_started = time.perf_counter()
            run = retriever.retrieve_control_and_augmented(case["question"], top_k=50)
            total_seconds = time.perf_counter() - query_started
            control = run["control"]
            augmented = run["augmented"]
            control_results = [compact_result(item, rank) for rank, item in enumerate(control["results"], 1)]
            augmented_results = [compact_result(item, rank) for rank, item in enumerate(augmented["results"], 1)]
            saved_control = case["minilm_graph_top_50_or_available"]
            if [item["table"] for item in control_results] != [item["table"] for item in saved_control]:
                raise RuntimeError(f"STOP: frozen control ranking mismatch for {case['id']}")
            for live, saved in zip(control_results, saved_control):
                if abs(live["final_score"] - saved["final_score"]) > 1e-12:
                    raise RuntimeError(f"STOP: frozen control score mismatch for {case['id']}")

            expected = case["expected_tables"]
            control_top10 = metric(expected, {item["table"] for item in control_results[:10]})
            augmented_top10 = metric(expected, {item["table"] for item in augmented_results[:10]})
            control_top50 = metric(expected, {item["table"] for item in control_results})
            augmented_top50 = metric(expected, {item["table"] for item in augmented_results})

            control_ranks = {item["table"]: item["rank"] for item in control_results}
            augmented_ranks = {item["table"]: item["rank"] for item in augmented_results}
            cap_expected = []
            for cap_row in augmented["cap_diagnostics"]:
                for excluded in cap_row["excluded_due_to_cap"]:
                    if excluded["target"] in expected:
                        cap_expected.append({
                            "expected_table": excluded["target"],
                            "seed_table": cap_row["seed_table"],
                            "seed_rank": cap_row["seed_rank"],
                            "excluded_position": 11 + cap_row["excluded_due_to_cap"].index(excluded),
                            "still_admitted_via_another_seed": excluded["target"] in {
                                item["table"] for item in augmented_results
                            },
                            "edge_families": excluded["families"],
                        })

            bge = [item["table"] for item in case["bge_dense_top_50"]]
            control_graph_names = [item["table"] for item in control_results]
            augmented_graph_names = [item["table"] for item in augmented_results]
            pools = {}
            for label, graph_names in (
                ("control_pool", control_graph_names),
                ("augmented_pool", augmented_graph_names),
            ):
                members = sorted(set(bge) | set(graph_names))
                pool_metric = metric(expected, set(members))
                pools[label] = {
                    "candidate_count": len(members),
                    "candidates": members,
                    **pool_metric,
                }

            row = {
                "id": case["id"], "question": case["question"],
                "difficulty": case["difficulty"], "domain": case["domain"],
                "expected_tables": expected,
                "control_candidate_set_size": control["expanded_candidate_pool_size"],
                "augmented_candidate_set_size": augmented["expanded_candidate_pool_size"],
                "control_top_50_returned": len(control_results),
                "augmented_top_50_returned": len(augmented_results),
                "control_results": control_results,
                "augmented_results": augmented_results,
                "control_at_10": control_top10,
                "augmented_at_10": augmented_top10,
                "control_at_50": control_top50,
                "augmented_at_50": augmented_top50,
                "expected_table_rank_changes": [{
                    "table": table,
                    "control_rank": control_ranks.get(table),
                    "augmented_rank": augmented_ranks.get(table),
                    "rank_delta_augmented_minus_control": (
                        augmented_ranks[table] - control_ranks[table]
                        if table in control_ranks and table in augmented_ranks else None
                    ),
                } for table in expected],
                "candidate_additions": sorted(set(augmented_graph_names) - set(control_graph_names)),
                "candidate_losses": sorted(set(control_graph_names) - set(augmented_graph_names)),
                "cap_diagnostics": augmented["cap_diagnostics"],
                "expected_table_cap_exclusions": cap_expected,
                "hybrid_retrieval_seconds": run["hybrid_seconds"],
                "control_expansion_and_ranking_seconds": control["expansion_and_ranking_seconds"],
                "augmented_expansion_seconds": augmented["expansion_seconds"],
                "augmented_ranking_seconds": augmented["ranking_seconds"],
                "augmented_total_query_seconds": total_seconds,
                **pools,
            }
            rows.append(row)
            timings["hybrid"].append(run["hybrid_seconds"])
            timings["control_expansion_ranking"].append(control["expansion_and_ranking_seconds"])
            timings["control_total"].append(
                run["hybrid_seconds"] + control["expansion_and_ranking_seconds"]
            )
            timings["augmented_expansion"].append(augmented["expansion_seconds"])
            timings["augmented_ranking"].append(augmented["ranking_seconds"])
            timings["augmented_total"].append(
                run["hybrid_seconds"] + augmented["expansion_and_ranking_seconds"]
            )
            timings["evaluation_wall_including_both_rankings"].append(total_seconds)
            print(f"{suite_name}: evaluated {ordinal}/{len(frozen_candidates['suites'][suite_name]['cases'])}", flush=True)
        control_macro = aggregate(rows, "control_at_10")["macro_recall"]
        if abs(control_macro - CONTROL_TOP10_TARGETS[suite_name]) > 1e-12:
            raise RuntimeError(f"STOP: control Recall@10 mismatch for {suite_name}")
        all_rows[suite_name] = rows

    # The frozen 22-failure artifact is intentionally loaded only after evaluation.
    reranker = json.loads(RERANKER_RESULTS_PATH.read_text(encoding="utf-8"))
    frozen_failures = []
    for case in reranker["suites"]["real_world_observed_13"]["cases"]:
        for failure in case["miss_failures"]:
            if failure["classification"] == "A_candidate_generation_failure":
                frozen_failures.append((case["id"], failure["table"]))
    if len(frozen_failures) != 22:
        raise RuntimeError("STOP: frozen candidate-generation failure set changed")
    real_by_id = {row["id"]: row for row in all_rows["real_world_observed_13"]}
    recovery_diagnostics = []
    for case_id, table in frozen_failures:
        row = real_by_id[case_id]
        control_result = next((x for x in row["control_results"] if x["table"] == table), None)
        new_result = next((x for x in row["augmented_results"] if x["table"] == table), None)
        recovered_graph = new_result is not None and control_result is None
        recovered_pool = table in row["augmented_pool"]["candidates"]
        if not recovered_graph and not recovered_pool:
            continue
        best_edge = None
        if new_result and new_result["source_edges"]:
            signals = [
                edge["hybrid_score"] / math.log2(edge["rank"] + 1)
                for edge in new_result["source_edges"]
            ]
            best_edge = new_result["source_edges"][signals.index(max(signals))]
        cap_rows = [
            item for item in row["expected_table_cap_exclusions"]
            if item["expected_table"] == table
        ]
        recovery_diagnostics.append({
            "case_id": case_id,
            "expected_table": table,
            "old_graph_status": "absent_from_graph_top_50",
            "old_graph_rank": None,
            "new_graph_rank": new_result["rank"] if new_result else None,
            "actual_seed": best_edge["table"] if best_edge else None,
            "seed_rank": best_edge["rank"] if best_edge else None,
            "seed_hybrid_score": best_edge["hybrid_score"] if best_edge else None,
            "one_hop_path": (
                [best_edge["table"], table] if best_edge else None
            ),
            "edge_family": best_edge["edge_families"] if best_edge else [],
            "edge_provenance": best_edge["edge_provenance"] if best_edge else [],
            "graph_contribution": new_result["fk_bonus_contribution"] if new_result else None,
            "cap_exclusion_evidence": cap_rows,
            "present_in_graph_top_50": new_result is not None,
            "present_in_augmented_combined_pool": recovered_pool,
        })

    suites_output = {}
    for suite_name, rows in all_rows.items():
        suites_output[suite_name] = {
            "graph": {
                "control_at_10": aggregate(rows, "control_at_10"),
                "augmented_at_10": aggregate(rows, "augmented_at_10"),
                "control_at_50": aggregate(rows, "control_at_50"),
                "augmented_at_50": aggregate(rows, "augmented_at_50"),
                "transitions_at_10": transitions(rows, "control_at_10", "augmented_at_10"),
                "transitions_at_50": transitions(rows, "control_at_50", "augmented_at_50"),
            },
            "candidate_pools": {
                "control_bge_dense_plus_graph": pool_summary(rows, "control_pool"),
                "augmented_bge_dense_plus_graph": pool_summary(rows, "augmented_pool"),
            },
            "cases": rows,
        }

    real = suites_output["real_world_observed_13"]
    conditions = {
        "real_world_graph_recall_at_50_increased": (
            real["graph"]["augmented_at_50"]["macro_recall"]
            > real["graph"]["control_at_50"]["macro_recall"]
        ),
        "real_world_combined_pool_recall_increased": (
            real["candidate_pools"]["augmented_bge_dense_plus_graph"]["macro_candidate_recall"]
            > real["candidate_pools"]["control_bge_dense_plus_graph"]["macro_candidate_recall"]
        ),
        "development_pool_recall_preserved": (
            suites_output["development_9"]["candidate_pools"]["augmented_bge_dense_plus_graph"]["macro_candidate_recall"]
            >= suites_output["development_9"]["candidate_pools"]["control_bge_dense_plus_graph"]["macro_candidate_recall"]
        ),
        "heldout_pool_recall_preserved": (
            suites_output["heldout_schema_20"]["candidate_pools"]["augmented_bge_dense_plus_graph"]["macro_candidate_recall"]
            >= suites_output["heldout_schema_20"]["candidate_pools"]["control_bge_dense_plus_graph"]["macro_candidate_recall"]
        ),
    }
    after = {relative: sha256_file(ROOT / relative) for relative in protected}
    if after != protected:
        raise RuntimeError("STOP: protected artifact changed during evaluation")

    result = {
        "experiment": "Bounded Reverse-FK + Explicit Form-Association Graph",
        "frozen_configuration": {
            "hybrid_seed_count": 10, "one_hop_only": True,
            "additional_neighbor_cap_per_seed": 10,
            "fk_bonus": 0.20, "multi_edge_bonus_accumulates": False,
            "production_depth": 10, "diagnostic_depth": 50,
            "primary_metric": "observed real-world macro candidate Recall@50",
        },
        "graph_artifact": {
            "path": "retrieval/augmented_relationship_graph.json",
            "sha256": sha256_file(GRAPH_PATH),
            "bytes": GRAPH_PATH.stat().st_size,
            "build_seconds": graph["build_seconds"],
            "additional_adjacency_approximate_python_bytes": deep_size(
                retriever.additional_adjacency
            ),
            "structural_validation": validation,
            "provenance_validation_passed": True,
        },
        "control_reproduction": {
            "all_saved_top50_rankings_and_scores_reproduced": True,
            "control_macro_recall_at_10": CONTROL_TOP10_TARGETS,
        },
        "suites": suites_output,
        "frozen_22_failure_recoveries": recovery_diagnostics,
        "cap_analysis": {
            "expected_table_exclusion_occurrences": [
                {"suite": suite, "case_id": row["id"], **item}
                for suite, rows in all_rows.items() for row in rows
                for item in row["expected_table_cap_exclusions"]
            ],
            "valid_generic_edge_but_absent_from_augmented_top50": [
                {"suite": suite, "case_id": row["id"], **item}
                for suite, rows in all_rows.items() for row in rows
                for item in row["expected_table_cap_exclusions"]
                if not item["still_admitted_via_another_seed"]
            ],
        },
        "latency_seconds": {key: timing_summary(value) for key, value in timings.items()},
        "acceptance_rule": {
            "conditions": conditions,
            "all_conditions_pass": all(conditions.values()),
            "decision": (
                "include augmentation in frozen candidate generator"
                if all(conditions.values()) else "retain existing retrieval architecture"
            ),
        },
        "integrity": {
            "graph_built_before_benchmark_loading": True,
            "protected_sha256_before": protected,
            "protected_sha256_after": after,
            "protected_artifacts_unchanged": True,
            "database_accessed": False, "sql_executed": False,
            "qwen_run": False, "support_tickets_accessed": False,
            "unseen_benchmark_accessed": False, "reranker_run": False,
            "embeddings_rebuilt": False, "faiss_rebuilt": False,
            "post_result_tuning": False, "polymorphic_edges_used": False,
            "manual_table_pairs_used": False,
        },
    }
    OUTPUT_PATH.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({
        "structural_validation": validation,
        "suite_summary": {
            name: {
                "control_graph_recall_at_10": data["graph"]["control_at_10"]["macro_recall"],
                "augmented_graph_recall_at_10": data["graph"]["augmented_at_10"]["macro_recall"],
                "control_graph_recall_at_50": data["graph"]["control_at_50"]["macro_recall"],
                "augmented_graph_recall_at_50": data["graph"]["augmented_at_50"]["macro_recall"],
                "control_pool_recall": data["candidate_pools"]["control_bge_dense_plus_graph"]["macro_candidate_recall"],
                "augmented_pool_recall": data["candidate_pools"]["augmented_bge_dense_plus_graph"]["macro_candidate_recall"],
            } for name, data in suites_output.items()
        },
        "recovered_frozen_failures": len(recovery_diagnostics),
        "acceptance_rule": result["acceptance_rule"],
    }, indent=2))


if __name__ == "__main__":
    main()
