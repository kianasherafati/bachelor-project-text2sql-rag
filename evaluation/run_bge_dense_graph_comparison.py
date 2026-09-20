"""Run the single frozen BGE-DenseGraph ablation evaluation."""

from __future__ import annotations

from collections import defaultdict
import hashlib
import json
import os
from pathlib import Path
import statistics
import sys


ROOT = Path(__file__).resolve().parents[1]
EVALUATION_DIR = ROOT / "evaluation"
RETRIEVAL_DIR = ROOT / "retrieval"
PREVIOUS_RESULTS_PATH = EVALUATION_DIR / "bge_m3_retrieval_comparison_results.json"
RESULT_PATH = EVALUATION_DIR / "bge_dense_graph_comparison_results.json"
HASHES_PATH = EVALUATION_DIR / "bge_dense_graph_protected_hashes_before.json"
sys.path.insert(0, str(EVALUATION_DIR))
sys.path.insert(0, str(RETRIEVAL_DIR))
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
os.environ.setdefault("OMP_NUM_THREADS", "8")
os.environ.setdefault("MKL_NUM_THREADS", "8")

from bge_dense_graph_retriever import BGEDenseGraphRetriever
from erp_retrieval_benchmark import tests as development_tests
from erp_retrieval_heldout_benchmark import tests as heldout_tests
from graph_expanded_retriever import FIXED_FK_BONUS, HYBRID_SEED_COUNT
from real_world_text2sql_benchmark import tests as real_world_tests


TOP_K = 10
NEW_SYSTEM = "BGE-DenseGraph"
PRIMARY_SYSTEMS = ("MiniLM Graph", "BGE-Dense", "BGE-Graph", NEW_SYSTEM)
TRANSITIONS = (
    ("BGE-Dense", NEW_SYSTEM),
    ("BGE-Graph", NEW_SYSTEM),
    ("MiniLM Graph", NEW_SYSTEM),
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def protected_paths():
    paths = [
        ROOT / "schema_extraction" / "schema_documents.json",
        RETRIEVAL_DIR / "bge_m3_schema.index",
        RETRIEVAL_DIR / "bge_m3_schema_metadata.json",
        RETRIEVAL_DIR / "bge_m3_model_manifest.json",
        RETRIEVAL_DIR / "bge_m3_schema_build_report.json",
        RETRIEVAL_DIR / "bge_m3_retriever.py",
        RETRIEVAL_DIR / "graph_expanded_retriever.py",
        RETRIEVAL_DIR / "hybrid_retriever.py",
        RETRIEVAL_DIR / "erp_retrieval_benchmark.py",
        RETRIEVAL_DIR / "erp_retrieval_heldout_benchmark.py",
        EVALUATION_DIR / "real_world_text2sql_benchmark.py",
        EVALUATION_DIR / "text2sql_gold_benchmark.py",
        EVALUATION_DIR / "text2sql_gold_validation.json",
        EVALUATION_DIR / "real_world_gold_benchmark.py",
        EVALUATION_DIR / "real_world_gold_validation.json",
        EVALUATION_DIR / "gold_sql_definitions.py",
        PREVIOUS_RESULTS_PATH,
    ]
    missing = [str(path.relative_to(ROOT)) for path in paths if not path.is_file()]
    if missing:
        raise FileNotFoundError(f"Protected artifacts missing: {missing}")
    return paths


def hashes(paths):
    return {
        str(path.relative_to(ROOT)): sha256_file(path)
        for path in paths
    }


def write_json(path: Path, value):
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def suite_definitions():
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


def aggregate(rows, field=None):
    groups = defaultdict(list)
    for row in rows:
        key = row.get(field) if field else "overall"
        if key is not None:
            groups[key].append(row)
    return {
        key: {
            "question_count": len(group),
            "macro_recall_at_10": statistics.mean(
                item["recall_at_10"] for item in group
            ),
            "full_coverage_count": sum(item["full_coverage"] for item in group),
        }
        for key, group in sorted(groups.items())
    }


def evaluate_new(case, run):
    results = run["results"]
    if len(results) != TOP_K or len({item["full_name"] for item in results}) != TOP_K:
        raise ValueError(f"{case['id']} did not return ten distinct final tables")
    expected = list(case["expected_tables"])
    retrieved = {item["full_name"] for item in results}
    missing = [table for table in expected if table not in retrieved]
    hits = len(expected) - len(missing)
    return {
        "id": case["id"],
        "question": case["question"],
        "difficulty": case.get("difficulty"),
        "domain": case.get("domain"),
        "expected_tables": expected,
        "retrieved_top_10": [
            {
                "final_rank": item["final_rank"],
                "table": item["full_name"],
                "raw_bge_cosine": item["raw_bge_cosine"],
                "normalized_bge_dense_score": item["dense_score"],
                "bge_dense_rank": item["bge_dense_rank"],
                "is_original_dense_seed": item["is_bge_dense_seed"],
                "graph_source_seeds": item["source_seeds"],
                "graph_signal": item["graph_signal"],
                "fk_bonus": item["fk_bonus_contribution"],
                "final_score": item["final_score"],
            }
            for item in results
        ],
        "missing_expected_tables": missing,
        "expected_tables_retrieved": hits,
        "recall_at_10": hits / len(expected),
        "full_coverage": hits == len(expected),
        "expanded_candidate_pool_size": run["expanded_candidate_pool_size"],
    }


def expected_diagnostics(case, run, reverse_direction_targets):
    dense = {
        item["full_name"]: item for item in run["all_dense_results"]
    }
    expanded = {
        item["full_name"]: item for item in run["all_expanded_candidates"]
    }
    seed_names = {
        item["full_name"] for item in run["original_bge_dense_top_10"]
    }
    output = []
    for table in case["expected_tables"]:
        dense_item = dense[table]
        candidate = expanded.get(table)
        reverse_sources = sorted(
            set(reverse_direction_targets.get(table, ())) & seed_names
        )
        if dense_item["global_dense_rank"] <= TOP_K:
            category = "dense semantic table found as a seed"
        elif candidate is not None and candidate["source_seed_tables"]:
            if candidate["final_rank"] <= TOP_K:
                category = "expected table recovered by outgoing FK"
            else:
                category = "FK-eligible expected table displaced after graph expansion"
        elif reverse_sources:
            category = "unreachable from seeds because the available FK direction is reversed"
        elif case["id"] in {"REAL-C01", "REAL-C02"}:
            category = "logical/polymorphic relationship not represented by the FK graph"
        else:
            category = "dense semantic miss with no eligible outgoing-FK seed"
        output.append({
            "expected_table": table,
            "dense_rank": dense_item["global_dense_rank"],
            "raw_bge_cosine": dense_item["raw_bge_cosine"],
            "normalized_bge_dense_score": dense_item["dense_score"],
            "dense_seed": dense_item["global_dense_rank"] <= TOP_K,
            "graph_candidate": candidate is not None,
            "graph_candidate_rank": candidate["final_rank"] if candidate else None,
            "final_top_10": candidate is not None and candidate["final_rank"] <= TOP_K,
            "graph_source_seeds": candidate["source_seeds"] if candidate else [],
            "reverse_direction_seed_tables": reverse_sources,
            "graph_signal": candidate["graph_signal"] if candidate else None,
            "fk_bonus": candidate["fk_bonus_contribution"] if candidate else None,
            "final_score": candidate["final_score"] if candidate else None,
            "failure_or_recovery_category": category,
        })
    return output


def previous_row(previous, suite_name, system, case_id):
    return next(
        row for row in previous["suites"][suite_name]["per_system"][system]
        if row["id"] == case_id
    )


def previous_expected(previous, suite_name, case_id, table, system):
    row = next(
        item
        for item in previous["full_expected_table_diagnostics"][suite_name][case_id]
        if item["expected_table"] == table
    )
    return row[system]


def transition(previous, suite_name, cases, new_rows, new_diagnostics, old_system):
    new_by_id = {row["id"]: row for row in new_rows}
    groups = {"improved": [], "unchanged": [], "regressed": []}
    evidence = []
    for case in cases:
        case_id = case["id"]
        old = previous_row(previous, suite_name, old_system, case_id)
        new = new_by_id[case_id]
        if new["recall_at_10"] > old["recall_at_10"]:
            classification = "improved"
        elif new["recall_at_10"] < old["recall_at_10"]:
            classification = "regressed"
        else:
            classification = "unchanged"
        groups[classification].append(case_id)
        old_top = {item["table"] for item in old["retrieved_top_10"]}
        new_top = {item["table"] for item in new["retrieved_top_10"]}
        diag_by_table = {
            item["expected_table"]: item for item in new_diagnostics[case_id]
        }
        changes = []
        for status, names in (
            ("gained", [name for name in case["expected_tables"] if name not in old_top and name in new_top]),
            ("lost", [name for name in case["expected_tables"] if name in old_top and name not in new_top]),
        ):
            for table in names:
                old_diag = previous_expected(
                    previous, suite_name, case_id, table, old_system
                )
                new_diag = diag_by_table[table]
                changes.append({
                    "status": status,
                    "expected_table": table,
                    "old_rank_or_status": old_diag["rank"],
                    "new_rank_or_status": new_diag["graph_candidate_rank"],
                    "bge_dense_rank": new_diag["dense_rank"],
                    "normalized_bge_dense_score": new_diag["normalized_bge_dense_score"],
                    "graph_source_seeds": new_diag["graph_source_seeds"],
                    "graph_contribution": new_diag["fk_bonus"],
                    "new_final_score": new_diag["final_score"],
                })
        evidence.append({
            "case_id": case_id,
            "classification": classification,
            "old_recall_at_10": old["recall_at_10"],
            "new_recall_at_10": new["recall_at_10"],
            "expected_table_changes": changes,
        })
    return {**groups, "per_case_evidence": evidence}


def latency_stats(values):
    return {
        "count": len(values),
        "mean_seconds": statistics.mean(values),
        "median_seconds": statistics.median(values),
        "maximum_seconds": max(values),
    }


def main():
    paths = protected_paths()
    before = hashes(paths)
    write_json(HASHES_PATH, {
        "status": "frozen_before_bge_dense_graph_evaluation",
        "sha256": before,
    })
    previous = json.loads(PREVIOUS_RESULTS_PATH.read_text(encoding="utf-8"))
    manifest = json.loads(
        (RETRIEVAL_DIR / "bge_m3_model_manifest.json").read_text(encoding="utf-8")
    )
    if manifest["resolved_model_revision"] != "5617a9f61b028005a4858fdac845db406aefb181":
        raise ValueError("Frozen BGE-M3 revision changed")
    suites = suite_definitions()
    retriever = BGEDenseGraphRetriever()
    retriever.warmup()
    # If an expected table points to a seed, that edge cannot be traversed from
    # the seed under the frozen outgoing-only graph policy.
    reverse_direction_targets = retriever.outgoing_adjacency

    suite_results = {}
    all_timings = {
        "total": [], "dense": [], "graph": [],
    }
    for suite_name, cases in suites.items():
        rows = []
        diagnostics = {}
        for case in cases:
            run = retriever.retrieve_bge_dense_graph(case["question"], top_k=TOP_K)
            row = evaluate_new(case, run)
            rows.append(row)
            diagnostics[case["id"]] = expected_diagnostics(
                case, run, reverse_direction_targets
            )
            all_timings["total"].append(run["timing"]["total_seconds"])
            all_timings["dense"].append(run["timing"]["dense_ranking_seconds"])
            all_timings["graph"].append(
                run["timing"]["graph_expansion_ranking_seconds"]
            )
            print(f"Evaluated {suite_name} {case['id']}", flush=True)
        overall = aggregate(rows)["overall"]
        eligible = [row for row in rows if row["id"] != "REAL-C04"]
        suite_results[suite_name] = {
            "per_case": rows,
            "aggregate": {
                **overall,
                "full_coverage_among_top10_eligible": sum(
                    row["full_coverage"] for row in eligible
                ),
                "top10_eligible_denominator": len(eligible),
                "by_difficulty": aggregate(rows, "difficulty"),
                "by_domain": aggregate(rows, "domain"),
            },
            "expected_table_diagnostics": diagnostics,
            "transitions": {
                f"{old} -> {NEW_SYSTEM}": transition(
                    previous, suite_name, cases, rows, diagnostics, old
                )
                for old, _ in TRANSITIONS
            },
        }

    real_c04 = next(
        row for row in suite_results["real_world_observed_13"]["per_case"]
        if row["id"] == "REAL-C04"
    )
    real_focus_ids = {
        "REAL-C01", "REAL-C02", "REAL-C04", "REAL-C05", "REAL-C06",
        "REAL-C07", "REAL-C08", "REAL-C09", "REAL-C14", "REAL-C15",
    }
    real_failure_analysis = {
        case_id: suite_results["real_world_observed_13"]
        ["expected_table_diagnostics"][case_id]
        for case_id in sorted(real_focus_ids)
    }

    after = hashes(paths)
    if after != before:
        changed = sorted(path for path in before if before[path] != after[path])
        raise ValueError(f"Protected artifacts changed: {changed}")
    previous_latency = previous["latency"]["query_latency"]
    result = {
        "experiment": "frozen_bge_dense_graph_ablation",
        "model_revision": manifest["resolved_model_revision"],
        "configuration": {
            "seeds": "first 10 distinct BGE-Dense tables",
            "seed_count": HYBRID_SEED_COUNT,
            "graph_hops": 1,
            "graph_direction": "outgoing",
            "fk_bonus": FIXED_FK_BONUS,
            "top_k": TOP_K,
            "lexical_stage_used": False,
        },
        "primary_comparison_aggregates": {
            suite_name: {
                system: (
                    suite_results[suite_name]["aggregate"]
                    if system == NEW_SYSTEM else
                    previous["suites"][suite_name]["aggregates"][system]
                )
                for system in PRIMARY_SYSTEMS
            }
            for suite_name in suites
        },
        "suites": suite_results,
        "real_c04": {
            "expected_table_count": 12,
            "retrieved_expected_table_count": real_c04["expected_tables_retrieved"],
            "recall_at_10": real_c04["recall_at_10"],
            "theoretical_ceiling": 10 / 12,
            "ceiling_reached": real_c04["expected_tables_retrieved"] == 10,
            "missing_expected_tables": real_c04["missing_expected_tables"],
        },
        "real_world_focus_failure_analysis": real_failure_analysis,
        "latency": {
            "BGE-Dense": previous_latency["BGE-Dense"],
            "BGE-Graph": previous_latency["BGE-Graph"],
            NEW_SYSTEM: latency_stats(all_timings["total"]),
            "BGE-DenseGraph_dense_stage": latency_stats(all_timings["dense"]),
            "BGE-DenseGraph_graph_stage_overhead": latency_stats(all_timings["graph"]),
        },
        "integrity": {
            "protected_artifacts_unchanged": True,
            "bge_index_rebuilt_or_reencoded": False,
            "model_revision_unchanged": True,
            "top_k_10": TOP_K == 10,
            "one_outgoing_fk_hop": True,
            "fk_bonus_0_20": FIXED_FK_BONUS == 0.20,
            "lexical_scorer_used": False,
            "aliases_used": False,
            "bm25_used": False,
            "chunks_used": False,
            "reranker_used": False,
            "database_accessed": False,
            "sql_executed": False,
            "qwen_run": False,
            "support_ticket_data_accessed": False,
            "unseen_tickets_inspected": False,
            "post_result_tuning": False,
        },
    }
    write_json(RESULT_PATH, result)
    print(json.dumps({
        suite: {
            "macro_recall_at_10": data["aggregate"]["macro_recall_at_10"],
            "full_coverage": data["aggregate"]["full_coverage_count"],
        }
        for suite, data in suite_results.items()
    }, indent=2))


if __name__ == "__main__":
    main()
