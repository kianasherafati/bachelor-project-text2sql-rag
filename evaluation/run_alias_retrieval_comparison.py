"""Run the frozen metadata-alias experiment across three diagnostic suites."""

from collections import defaultdict
import hashlib
import json
import os
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
EVALUATION_DIR = ROOT / "evaluation"
RETRIEVAL_DIR = ROOT / "retrieval"
RESULT_PATH = EVALUATION_DIR / "alias_retrieval_comparison_results.json"
sys.path.insert(0, str(EVALUATION_DIR))
sys.path.insert(0, str(RETRIEVAL_DIR))
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")

from alias_enriched_retriever import AliasEnrichedSchemaRetriever
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
MODES = ("Dense", "Hybrid", "Graph", "AliasHybrid", "AliasGraph")


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def protected_paths():
    paths = [
        RETRIEVAL_DIR / "retriever.py",
        RETRIEVAL_DIR / "hybrid_retriever.py",
        RETRIEVAL_DIR / "graph_expanded_retriever.py",
        RETRIEVAL_DIR / "schema.index",
        RETRIEVAL_DIR / "schema_metadata.pkl",
        ROOT / "schema_extraction" / "schema_documents.json",
        RETRIEVAL_DIR / "erp_retrieval_benchmark.py",
        RETRIEVAL_DIR / "erp_retrieval_heldout_benchmark.py",
        EVALUATION_DIR / "real_world_text2sql_benchmark.py",
        RETRIEVAL_DIR / "business_alias_catalog.json",
    ]
    paths.extend(
        path
        for path in EVALUATION_DIR.iterdir()
        if path.is_file()
        and "gold" in path.name.casefold()
        and path != RESULT_PATH
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
    if mode in ("Hybrid", "AliasHybrid"):
        return {
            "dense_score": result["dense_score"],
            "lexical_score": result["lexical_score"],
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
            {
                "rank": rank,
                "table": result["full_name"],
                **result_scores(mode, result),
            }
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
        value = row.get(field) if field else "overall"
        if value is not None:
            groups[value].append(row)
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


def transition(
    cases,
    old_mode,
    new_mode,
    evaluated,
    full_rankings,
    hybrid_rankings,
):
    outcome = {"improved": [], "unchanged": [], "regressed": [], "regressions": []}
    by_id = {
        mode: {row["id"]: row for row in evaluated[mode]}
        for mode in (old_mode, new_mode)
    }
    for case in cases:
        case_id = case["id"]
        old = by_id[old_mode][case_id]
        new = by_id[new_mode][case_id]
        if new["recall_at_10"] > old["recall_at_10"]:
            outcome["improved"].append(case_id)
        elif new["recall_at_10"] < old["recall_at_10"]:
            outcome["regressed"].append(case_id)
        else:
            outcome["unchanged"].append(case_id)

        if new["recall_at_10"] >= old["recall_at_10"]:
            continue
        old_top = {item["table"] for item in old["retrieved_top_10"]}
        new_top = {item["table"] for item in new["retrieved_top_10"]}
        lost = [
            table for table in case["expected_tables"]
            if table in old_top and table not in new_top
        ]
        old_ranks = rank_lookup(full_rankings[old_mode][case_id])
        new_ranks = rank_lookup(full_rankings[new_mode][case_id])
        baseline_hybrid = rank_lookup(hybrid_rankings["Hybrid"][case_id])
        alias_hybrid = rank_lookup(hybrid_rankings["AliasHybrid"][case_id])
        for table in lost:
            old_rank, old_result = old_ranks.get(table, (None, None))
            new_rank, new_result = new_ranks.get(table, (None, None))
            old_hybrid = baseline_hybrid.get(table, (None, None))[1]
            new_hybrid = alias_hybrid.get(table, (None, None))[1]
            outcome["regressions"].append({
                "case_id": case_id,
                "expected_table_lost": table,
                "old_rank": old_rank,
                "new_rank": new_rank,
                "old_lexical_score": (
                    old_hybrid["lexical_score"] if old_hybrid else None
                ),
                "new_lexical_score": (
                    new_hybrid["lexical_score"] if new_hybrid else None
                ),
                "old_final_score": (
                    old_result.get("final_score", old_result.get("combined_score"))
                    if old_result else None
                ),
                "new_final_score": (
                    new_result.get("final_score", new_result.get("combined_score"))
                    if new_result else None
                ),
            })
    return outcome


def improvement_evidence(
    retriever,
    cases,
    old_mode,
    new_mode,
    transition_result,
    evaluated,
    full_rankings,
):
    old_by_id = {row["id"]: row for row in evaluated[old_mode]}
    new_by_id = {row["id"]: row for row in evaluated[new_mode]}
    case_by_id = {case["id"]: case for case in cases}
    report = []
    for case_id in transition_result["improved"]:
        case = case_by_id[case_id]
        old_top = {item["table"] for item in old_by_id[case_id]["retrieved_top_10"]}
        new_top = {item["table"] for item in new_by_id[case_id]["retrieved_top_10"]}
        gained = [
            table for table in case["expected_tables"]
            if table not in old_top and table in new_top
        ]
        new_ranks = rank_lookup(full_rankings[new_mode][case_id])
        tables = []
        for table in gained:
            _, result = new_ranks[table]
            target_evidence = retriever.alias_evidence(case["question"], table)
            seed_evidence = []
            if new_mode == "AliasGraph":
                for seed in result.get("source_seed_tables", []):
                    evidence = retriever.alias_evidence(case["question"], seed)
                    if evidence:
                        seed_evidence.append({"seed_table": seed, "evidence": evidence})
            tables.append({
                "newly_retrieved_expected_table": table,
                "target_alias_evidence": target_evidence,
                "source_seed_alias_evidence": seed_evidence,
                "interpretation": "supporting_evidence_not_causal_proof",
            })
        report.append({"case_id": case_id, "tables": tables})
    return report


def print_suite_report(name, suite_result):
    print("=" * 100)
    print("SUITE", name)
    for mode in MODES:
        overall = suite_result["aggregates"][mode]["overall"]
        print(
            f"{mode}: macro Recall@10={overall['macro_recall_at_10']:.4f}; "
            f"full={overall['fully_covered_questions']}/{overall['questions']}"
        )
        for row in suite_result["cases"][mode]:
            missing = ", ".join(row["missing_expected_tables"]) or "None"
            print(
                f"  {row['id']}: recall={row['recall_at_10']:.4f}; "
                f"missing={missing}"
            )
        if suite_result["aggregates"][mode].get("by_difficulty"):
            print("  by difficulty:", suite_result["aggregates"][mode]["by_difficulty"])
        if suite_result["aggregates"][mode].get("by_domain"):
            print("  by domain:", suite_result["aggregates"][mode]["by_domain"])
    for label, result in suite_result["transitions"].items():
        print(label, {
            "improved": result["improved"],
            "unchanged": result["unchanged"],
            "regressed": result["regressed"],
        })


def run():
    assert TOP_K == 10
    assert DENSE_WEIGHT == 0.70 and LEXICAL_WEIGHT == 0.30
    assert FIXED_FK_BONUS == 0.20 and HYBRID_SEED_COUNT == 10
    assert EMBEDDING_MODEL_NAME == "sentence-transformers/all-MiniLM-L6-v2"
    paths = protected_paths()
    before_hashes = hashes(paths)

    retriever = AliasEnrichedSchemaRetriever()
    assert retriever.index.ntotal == len(retriever.documents) == 2196
    indexed = {document["full_name"] for document in retriever.documents}
    suites = suite_definitions()
    assert len(suites["development_9"]) == 9
    assert len(suites["heldout_schema_20"]) == 20
    assert len(suites["real_world_observed_13"]) == 13

    report = {
        "experiment": "metadata_driven_business_alias_enrichment",
        "top_k": TOP_K,
        "systems": list(MODES),
        "real_world_suite_status": "observed_development_stress_set",
        "alias_statistics": retriever.alias_statistics(),
        "suites": {},
        "integrity": {},
    }

    for suite_name, cases in suites.items():
        if any(table not in indexed for case in cases for table in case["expected_tables"]):
            raise ValueError(f"Expected table outside indexed corpus in {suite_name}")
        evaluated = {mode: [] for mode in MODES}
        full_rankings = {mode: {} for mode in MODES}
        hybrid_rankings = {"Hybrid": {}, "AliasHybrid": {}}
        for case in cases:
            dense_top = retriever.retrieve(case["question"], top_k=TOP_K)
            hybrid_all = retriever.retrieve_hybrid(
                case["question"], top_k=retriever.index.ntotal
            )
            graph_all, _ = rank_expanded_candidates(
                hybrid_all,
                hybrid_all[:HYBRID_SEED_COUNT],
                retriever.outgoing_adjacency,
                retriever.index.ntotal,
            )
            alias_all = retriever.retrieve_alias_hybrid(
                case["question"], top_k=retriever.index.ntotal
            )
            alias_graph_all, _ = rank_expanded_candidates(
                alias_all,
                alias_all[:HYBRID_SEED_COUNT],
                retriever.outgoing_adjacency,
                retriever.index.ntotal,
            )
            mode_results = {
                "Dense": dense_top,
                "Hybrid": hybrid_all[:TOP_K],
                "Graph": graph_all[:TOP_K],
                "AliasHybrid": alias_all[:TOP_K],
                "AliasGraph": alias_graph_all[:TOP_K],
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
            full_rankings["AliasHybrid"][case["id"]] = alias_all
            full_rankings["AliasGraph"][case["id"]] = alias_graph_all
            hybrid_rankings["Hybrid"][case["id"]] = hybrid_all
            hybrid_rankings["AliasHybrid"][case["id"]] = alias_all

        transitions = {
            "Hybrid_to_AliasHybrid": transition(
                cases, "Hybrid", "AliasHybrid", evaluated,
                full_rankings, hybrid_rankings,
            ),
            "Graph_to_AliasGraph": transition(
                cases, "Graph", "AliasGraph", evaluated,
                full_rankings, hybrid_rankings,
            ),
        }
        evidence = {
            "Hybrid_to_AliasHybrid": improvement_evidence(
                retriever, cases, "Hybrid", "AliasHybrid",
                transitions["Hybrid_to_AliasHybrid"], evaluated, full_rankings,
            ),
            "Graph_to_AliasGraph": improvement_evidence(
                retriever, cases, "Graph", "AliasGraph",
                transitions["Graph_to_AliasGraph"], evaluated, full_rankings,
            ),
        }
        aggregates = {}
        for mode in MODES:
            aggregates[mode] = {
                "overall": aggregate(evaluated[mode])["overall"],
                "by_difficulty": aggregate(evaluated[mode], "difficulty"),
                "by_domain": aggregate(evaluated[mode], "domain"),
            }
        suite_result = {
            "cases": evaluated,
            "aggregates": aggregates,
            "transitions": transitions,
            "alias_supporting_evidence": evidence,
        }
        if suite_name == "real_world_observed_13":
            c04 = {
                mode: next(
                    row for row in evaluated[mode] if row["id"] == "REAL-C04"
                )
                for mode in MODES
            }
            suite_result["REAL_C04"] = {
                mode: {
                    "expected_tables_retrieved": row["expected_tables_retrieved"],
                    "expected_table_count": 12,
                    "recall_at_10": row["recall_at_10"],
                    "theoretical_ceiling": 10 / 12,
                    "ceiling_reached": row["expected_tables_retrieved"] == 10,
                    "missing_expected_tables": row["missing_expected_tables"],
                }
                for mode, row in c04.items()
            }
        report["suites"][suite_name] = suite_result
        print_suite_report(suite_name, suite_result)

    after_hashes = hashes(paths)
    if before_hashes != after_hashes:
        raise ValueError("A frozen baseline, benchmark, alias input, or gold file changed")
    report["integrity"] = {
        "indexed_table_count": 2196,
        "protected_file_hashes_unchanged": True,
        "faiss_index_unchanged": True,
        "embedding_metadata_unchanged": True,
        "original_hybrid_code_unchanged": True,
        "original_graph_code_unchanged": True,
        "benchmark_files_unchanged": True,
        "gold_sql_files_unchanged": True,
        "top_k": TOP_K,
        "hybrid_weights": {"dense": DENSE_WEIGHT, "lexical": LEXICAL_WEIGHT},
        "fk_bonus": FIXED_FK_BONUS,
        "graph_policy": "one_hop_outgoing_fk",
        "support_ticket_content_used": False,
        "manually_invented_synonyms_used": False,
        "parameters_tuned_after_results": False,
        "protected_sha256": after_hashes,
    }
    RESULT_PATH.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print("=" * 100)
    print("RESULT", RESULT_PATH)
    print(json.dumps(report["alias_statistics"], indent=2))
    print("Integrity checks passed")
    return report


if __name__ == "__main__":
    run()
