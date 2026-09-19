"""Evaluate frozen baselines against the controlled BM25 experiment."""

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
RESULT_PATH = EVALUATION_DIR / "bm25_retrieval_comparison_results.json"
sys.path.insert(0, str(EVALUATION_DIR))
sys.path.insert(0, str(RETRIEVAL_DIR))
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")

from bm25_hybrid_retriever import BM25_B, BM25_K1, BM25HybridSchemaRetriever
from erp_retrieval_benchmark import tests as development_tests
from erp_retrieval_heldout_benchmark import tests as heldout_tests
from graph_expanded_retriever import (
    FIXED_FK_BONUS,
    HYBRID_SEED_COUNT,
    rank_expanded_candidates,
)
from hybrid_retriever import DENSE_WEIGHT, LEXICAL_WEIGHT
from real_world_text2sql_benchmark import tests as real_world_tests
from retriever import EMBEDDING_MODEL_NAME


TOP_K = 10
MODES = ("Dense", "Hybrid", "Graph", "BM25Hybrid", "BM25Graph")


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def protected_paths():
    paths = [
        RETRIEVAL_DIR / "retriever.py",
        RETRIEVAL_DIR / "hybrid_retriever.py",
        RETRIEVAL_DIR / "graph_expanded_retriever.py",
        RETRIEVAL_DIR / "alias_enriched_retriever.py",
        RETRIEVAL_DIR / "schema.index",
        RETRIEVAL_DIR / "schema_metadata.pkl",
        ROOT / "schema_extraction" / "schema_documents.json",
        RETRIEVAL_DIR / "erp_retrieval_benchmark.py",
        RETRIEVAL_DIR / "erp_retrieval_heldout_benchmark.py",
        EVALUATION_DIR / "real_world_text2sql_benchmark.py",
    ]
    for name in (
        "business_alias_source.json",
        "business_alias_catalog.json",
        "business_alias_translation_queue.json",
    ):
        path = RETRIEVAL_DIR / name
        if path.exists():
            paths.append(path)
    paths.extend(
        path for path in EVALUATION_DIR.iterdir()
        if path.is_file() and "gold" in path.name.casefold()
    )
    return sorted(set(paths))


def hashes(paths):
    return {str(path.relative_to(ROOT)): sha256(path) for path in paths}


def suite_definitions():
    development = []
    for index, case in enumerate(development_tests, start=1):
        item = dict(case)
        item["id"] = f"DEV-{index:02d}"
        development.append(item)
    return {
        "development_9": development,
        "heldout_schema_20": [dict(case) for case in heldout_tests],
        "real_world_observed_13": [dict(case) for case in real_world_tests],
    }


def result_scores(mode, result):
    if mode == "Dense":
        return {"dense_raw_score": result["score"]}
    if mode == "Hybrid":
        return {
            "dense_score": result["dense_score"],
            "lexical_score": result["lexical_score"],
            "combined_score": result["combined_score"],
        }
    if mode == "BM25Hybrid":
        return {
            "dense_score": result["dense_score"],
            "bm25_raw_score": result["bm25_raw_score"],
            "bm25_score": result["bm25_score"],
            "combined_score": result["combined_score"],
        }
    return {
        "hybrid_score": result["hybrid_score"],
        "graph_signal": result["graph_signal"],
        "fk_bonus_contribution": result["fk_bonus_contribution"],
        "final_score": result["final_score"],
        "is_seed": result["is_hybrid_seed"],
        "source_seed_tables": result["source_seed_tables"],
    }


def evaluate_case(case, mode, top_results):
    expected = list(case["expected_tables"])
    retrieved = [result["full_name"] for result in top_results]
    retrieved_set = set(retrieved)
    missing = [table for table in expected if table not in retrieved_set]
    hits = len(expected) - len(missing)
    return {
        "id": case["id"],
        "question": case["question"],
        "difficulty": case.get("difficulty"),
        "domain": case.get("domain"),
        "expected_tables": expected,
        "retrieved_top_10": [
            {"rank": rank, "table": result["full_name"], **result_scores(mode, result)}
            for rank, result in enumerate(top_results, start=1)
        ],
        "missing_expected_tables": missing,
        "expected_tables_retrieved": hits,
        "recall_at_10": hits / len(expected),
        "full_coverage": hits == len(expected),
    }


def aggregate(rows, field=None):
    groups = defaultdict(list)
    for row in rows:
        key = row.get(field) if field else "overall"
        if key is not None:
            groups[key].append(row)
    return {
        key: {
            "questions": len(group),
            "macro_recall_at_10": sum(x["recall_at_10"] for x in group) / len(group),
            "fully_covered_questions": sum(x["full_coverage"] for x in group),
        }
        for key, group in sorted(groups.items())
    }


def rank_lookup(results):
    return {
        result["full_name"]: (rank, result)
        for rank, result in enumerate(results, start=1)
    }


def transition(cases, old_mode, new_mode, evaluated, full_rankings, hybrid_rankings):
    output = {"improved": [], "unchanged": [], "regressed": [], "regressions": []}
    by_id = {
        mode: {row["id"]: row for row in evaluated[mode]}
        for mode in (old_mode, new_mode)
    }
    for case in cases:
        case_id = case["id"]
        old = by_id[old_mode][case_id]
        new = by_id[new_mode][case_id]
        if new["recall_at_10"] > old["recall_at_10"]:
            output["improved"].append(case_id)
        elif new["recall_at_10"] < old["recall_at_10"]:
            output["regressed"].append(case_id)
        else:
            output["unchanged"].append(case_id)
        if new["recall_at_10"] >= old["recall_at_10"]:
            continue

        old_top = {item["table"] for item in old["retrieved_top_10"]}
        new_top = {item["table"] for item in new["retrieved_top_10"]}
        old_ranks = rank_lookup(full_rankings[old_mode][case_id])
        new_ranks = rank_lookup(full_rankings[new_mode][case_id])
        old_hybrid = rank_lookup(hybrid_rankings["Hybrid"][case_id])
        bm25_hybrid = rank_lookup(hybrid_rankings["BM25Hybrid"][case_id])
        for table in case["expected_tables"]:
            if table not in old_top or table in new_top:
                continue
            old_rank, old_result = old_ranks.get(table, (None, None))
            new_rank, new_result = new_ranks.get(table, (None, None))
            old_lexical = old_hybrid.get(table, (None, None))[1]
            new_bm25 = bm25_hybrid.get(table, (None, None))[1]
            output["regressions"].append({
                "case_id": case_id,
                "expected_table_lost": table,
                "old_rank": old_rank,
                "new_rank": new_rank,
                "old_lexical_score": old_lexical["lexical_score"],
                "bm25_normalized_score": new_bm25["bm25_score"],
                "bm25_raw_score": new_bm25["bm25_raw_score"],
                "old_final_score": (
                    old_result.get("final_score", old_result.get("combined_score"))
                    if old_result else None
                ),
                "new_final_score": (
                    new_result.get("final_score", new_result.get("combined_score"))
                    if new_result else None
                ),
            })
    return output


def improvement_analysis(
    retriever, cases, old_mode, new_mode, transition_result,
    evaluated, full_rankings,
):
    old_by_id = {row["id"]: row for row in evaluated[old_mode]}
    new_by_id = {row["id"]: row for row in evaluated[new_mode]}
    case_by_id = {case["id"]: case for case in cases}
    analysis = []
    for case_id in transition_result["improved"]:
        case = case_by_id[case_id]
        old = old_by_id[case_id]
        new = new_by_id[case_id]
        old_top = {item["table"] for item in old["retrieved_top_10"]}
        new_top = {item["table"] for item in new["retrieved_top_10"]}
        gained = [
            table for table in case["expected_tables"]
            if table not in old_top and table in new_top
        ]
        old_ranks = rank_lookup(full_rankings[old_mode][case_id])
        new_ranks = rank_lookup(full_rankings[new_mode][case_id])
        demoted = []
        for table in sorted(old_top - new_top):
            old_rank, old_result = old_ranks.get(table, (None, None))
            new_rank, new_result = new_ranks.get(table, (None, None))
            demoted.append({
                "table": table,
                "old_rank": old_rank,
                "new_rank": new_rank,
                "old_score": (
                    old_result.get("final_score", old_result.get("combined_score"))
                    if old_result else None
                ),
                "new_score": (
                    new_result.get("final_score", new_result.get("combined_score"))
                    if new_result else None
                ),
            })
        gained_details = []
        for table in gained:
            _, result = new_ranks[table]
            source_seed_details = []
            if new_mode == "BM25Graph":
                for seed in result.get("source_seed_tables", []):
                    source_seed_details.append({
                        "seed_table": seed,
                        "bm25_term_details": retriever.bm25_term_details(
                            case["question"], seed
                        ),
                    })
            gained_details.append({
                "newly_retrieved_expected_table": table,
                "bm25_term_details": retriever.bm25_term_details(
                    case["question"], table
                ),
                "source_seed_term_details": source_seed_details,
            })
        analysis.append({
            "case_id": case_id,
            "gained_expected_tables": gained_details,
            "old_top_10_tables_demoted": demoted,
            "interpretation": "descriptive_BM25_evidence_not_causal_ablation",
        })
    return analysis


def saturation_aggregate(per_case):
    output = {}
    for scorer in ("old_lexical", "normalized_bm25"):
        rows = [item[scorer] for item in per_case]
        output[scorer] = {
            "mean_tables_at_maximum": statistics.mean(
                row["tables_at_maximum"] for row in rows
            ),
            "mean_tables_near_maximum": statistics.mean(
                row["tables_near_maximum"] for row in rows
            ),
            "mean_top_score_ties": statistics.mean(
                row["top_score_ties"] for row in rows
            ),
            "mean_top_20_score_spread": statistics.mean(
                row["top_20_score_spread"] for row in rows
            ),
        }
    return output


def print_suite(name, suite):
    print("=" * 100)
    print("SUITE", name)
    for mode in MODES:
        overall = suite["aggregates"][mode]["overall"]
        print(
            f"{mode}: macro Recall@10={overall['macro_recall_at_10']:.4f}; "
            f"full={overall['fully_covered_questions']}/{overall['questions']}"
        )
        for row in suite["cases"][mode]:
            missing = ", ".join(row["missing_expected_tables"]) or "None"
            print(f"  {row['id']}: recall={row['recall_at_10']:.4f}; missing={missing}")
    for label, item in suite["transitions"].items():
        print(label, {
            "improved": item["improved"],
            "unchanged": item["unchanged"],
            "regressed": item["regressed"],
        })
    print("SATURATION", suite["lexical_saturation"]["aggregate"])


def run():
    assert TOP_K == 10
    assert BM25_K1 == 1.5 and BM25_B == 0.75
    assert DENSE_WEIGHT == 0.70 and LEXICAL_WEIGHT == 0.30
    assert FIXED_FK_BONUS == 0.20 and HYBRID_SEED_COUNT == 10
    assert EMBEDDING_MODEL_NAME == "sentence-transformers/all-MiniLM-L6-v2"
    paths = protected_paths()
    before_hashes = hashes(paths)

    retriever = BM25HybridSchemaRetriever()
    assert retriever.index.ntotal == len(retriever.documents) == 2196
    indexed = {document["full_name"] for document in retriever.documents}
    suites = suite_definitions()
    assert {name: len(cases) for name, cases in suites.items()} == {
        "development_9": 9,
        "heldout_schema_20": 20,
        "real_world_observed_13": 13,
    }

    report = {
        "experiment": "controlled_bm25_original_lexical_content",
        "parameters": {
            "top_k": TOP_K,
            "bm25_k1": BM25_K1,
            "bm25_b": BM25_B,
            "bm25_normalization": "raw_score / maximum_raw_score_for_query",
            "dense_weight": DENSE_WEIGHT,
            "lexical_weight": LEXICAL_WEIGHT,
            "fk_bonus": FIXED_FK_BONUS,
            "graph_policy": "one_hop_outgoing_fk",
        },
        "systems": list(MODES),
        "real_world_suite_status": "observed_development_stress_set",
        "suites": {},
        "integrity": {},
    }

    for suite_name, cases in suites.items():
        if any(table not in indexed for case in cases for table in case["expected_tables"]):
            raise ValueError(f"Expected table outside corpus in {suite_name}")
        evaluated = {mode: [] for mode in MODES}
        full_rankings = {mode: {} for mode in MODES}
        hybrid_rankings = {"Hybrid": {}, "BM25Hybrid": {}}
        saturation = []
        for case in cases:
            question = case["question"]
            dense_top = retriever.retrieve(question, top_k=TOP_K)
            hybrid_all = retriever.retrieve_hybrid(
                question, top_k=retriever.index.ntotal
            )
            graph_all, _ = rank_expanded_candidates(
                hybrid_all, hybrid_all[:HYBRID_SEED_COUNT],
                retriever.outgoing_adjacency, retriever.index.ntotal,
            )
            bm25_all = retriever.retrieve_bm25_hybrid(
                question, top_k=retriever.index.ntotal
            )
            bm25_graph_all, _ = rank_expanded_candidates(
                bm25_all, bm25_all[:HYBRID_SEED_COUNT],
                retriever.outgoing_adjacency, retriever.index.ntotal,
            )
            mode_results = {
                "Dense": dense_top,
                "Hybrid": hybrid_all[:TOP_K],
                "Graph": graph_all[:TOP_K],
                "BM25Hybrid": bm25_all[:TOP_K],
                "BM25Graph": bm25_graph_all[:TOP_K],
            }
            for mode, top_results in mode_results.items():
                if len(top_results) != TOP_K:
                    raise ValueError(
                        f"{suite_name}/{case['id']}/{mode} returned {len(top_results)}"
                    )
                evaluated[mode].append(evaluate_case(case, mode, top_results))
            full_rankings["Dense"][case["id"]] = dense_top
            full_rankings["Hybrid"][case["id"]] = hybrid_all
            full_rankings["Graph"][case["id"]] = graph_all
            full_rankings["BM25Hybrid"][case["id"]] = bm25_all
            full_rankings["BM25Graph"][case["id"]] = bm25_graph_all
            hybrid_rankings["Hybrid"][case["id"]] = hybrid_all
            hybrid_rankings["BM25Hybrid"][case["id"]] = bm25_all
            stats = retriever.lexical_saturation_statistics(
                question,
                [result["lexical_score"] for result in hybrid_all],
            )
            saturation.append({"case_id": case["id"], **stats})

        transitions = {
            "Hybrid_to_BM25Hybrid": transition(
                cases, "Hybrid", "BM25Hybrid", evaluated,
                full_rankings, hybrid_rankings,
            ),
            "Graph_to_BM25Graph": transition(
                cases, "Graph", "BM25Graph", evaluated,
                full_rankings, hybrid_rankings,
            ),
        }
        improvements = {
            "Hybrid_to_BM25Hybrid": improvement_analysis(
                retriever, cases, "Hybrid", "BM25Hybrid",
                transitions["Hybrid_to_BM25Hybrid"], evaluated, full_rankings,
            ),
            "Graph_to_BM25Graph": improvement_analysis(
                retriever, cases, "Graph", "BM25Graph",
                transitions["Graph_to_BM25Graph"], evaluated, full_rankings,
            ),
        }
        aggregates = {
            mode: {
                "overall": aggregate(evaluated[mode])["overall"],
                "by_difficulty": aggregate(evaluated[mode], "difficulty"),
                "by_domain": aggregate(evaluated[mode], "domain"),
            }
            for mode in MODES
        }
        suite_result = {
            "cases": evaluated,
            "aggregates": aggregates,
            "transitions": transitions,
            "improvement_analysis": improvements,
            "lexical_saturation": {
                "near_maximum_definition": ">= 95% of query maximum",
                "per_case": saturation,
                "aggregate": saturation_aggregate(saturation),
            },
        }
        if suite_name == "real_world_observed_13":
            suite_result["REAL_C04"] = {
                mode: {
                    "expected_tables_retrieved": row["expected_tables_retrieved"],
                    "expected_table_count": 12,
                    "recall_at_10": row["recall_at_10"],
                    "theoretical_ceiling": 10 / 12,
                    "ceiling_reached": row["expected_tables_retrieved"] == 10,
                    "missing_expected_tables": row["missing_expected_tables"],
                }
                for mode in MODES
                for row in evaluated[mode]
                if row["id"] == "REAL-C04"
            }
        report["suites"][suite_name] = suite_result
        print_suite(suite_name, suite_result)

    after_hashes = hashes(paths)
    if before_hashes != after_hashes:
        raise ValueError("A frozen artifact changed during BM25 evaluation")
    report["integrity"] = {
        "indexed_table_count": 2196,
        "protected_file_hashes_unchanged": True,
        "embeddings_and_faiss_unchanged": True,
        "original_retrievers_unchanged": True,
        "alias_retriever_and_artifacts_unchanged": True,
        "alias_artifacts_used_by_bm25": False,
        "benchmark_files_unchanged": True,
        "gold_sql_files_unchanged": True,
        "database_accessed": False,
        "qwen_run": False,
        "sql_executed": False,
        "parameters_tuned_after_results": False,
        "protected_sha256": after_hashes,
    }
    RESULT_PATH.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print("=" * 100)
    print("RESULT", RESULT_PATH)
    print("Integrity checks passed")
    return report


if __name__ == "__main__":
    run()
