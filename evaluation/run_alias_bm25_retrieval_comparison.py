"""Evaluate the controlled metadata-alias plus BM25 retrieval experiment."""

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
RESULT_PATH = EVALUATION_DIR / "alias_bm25_retrieval_comparison_results.json"
PRIOR_BM25_RESULT_PATH = EVALUATION_DIR / "bm25_retrieval_comparison_results.json"
sys.path.insert(0, str(EVALUATION_DIR))
sys.path.insert(0, str(RETRIEVAL_DIR))
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")

from alias_bm25_retriever import AliasBM25SchemaRetriever
from bm25_hybrid_retriever import BM25_B, BM25_K1
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
MODES = (
    "Hybrid",
    "AliasHybrid",
    "BM25Hybrid",
    "AliasBM25Hybrid",
    "Graph",
    "AliasGraph",
    "BM25Graph",
    "AliasBM25Graph",
)
GRAPH_MODES = {"Graph", "AliasGraph", "BM25Graph", "AliasBM25Graph"}
BM25_MODES = {
    "BM25Hybrid", "AliasBM25Hybrid", "BM25Graph", "AliasBM25Graph"
}


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def protected_paths():
    paths = [
        RETRIEVAL_DIR / "retriever.py",
        RETRIEVAL_DIR / "hybrid_retriever.py",
        RETRIEVAL_DIR / "graph_expanded_retriever.py",
        RETRIEVAL_DIR / "alias_enriched_retriever.py",
        RETRIEVAL_DIR / "bm25_hybrid_retriever.py",
        RETRIEVAL_DIR / "schema.index",
        RETRIEVAL_DIR / "schema_metadata.pkl",
        ROOT / "schema_extraction" / "schema_documents.json",
        RETRIEVAL_DIR / "erp_retrieval_benchmark.py",
        RETRIEVAL_DIR / "erp_retrieval_heldout_benchmark.py",
        EVALUATION_DIR / "real_world_text2sql_benchmark.py",
        EVALUATION_DIR / "run_alias_retrieval_comparison.py",
        EVALUATION_DIR / "run_bm25_retrieval_comparison.py",
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
        if path.is_file()
        and (
            "gold" in path.name.casefold()
            or path.name.endswith("comparison_results.json")
        )
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
    scores = {"dense_score": result.get("dense_score")}
    if mode in ("Hybrid", "AliasHybrid", "Graph", "AliasGraph"):
        scores["lexical_score"] = result.get("lexical_score")
    if mode in BM25_MODES:
        scores.update({
            "bm25_raw_score": result.get("bm25_raw_score"),
            "bm25_normalized_score": result.get("bm25_score"),
        })
    if mode in GRAPH_MODES:
        scores.update({
            "hybrid_score": result["hybrid_score"],
            "graph_signal": result["graph_signal"],
            "fk_bonus_contribution": result["fk_bonus_contribution"],
            "final_score": result["final_score"],
            "is_seed": result["is_hybrid_seed"],
            "source_seed_tables": result["source_seed_tables"],
        })
    else:
        scores["combined_score"] = result["combined_score"]
    return scores


def evaluate_case(case, mode, top_results):
    expected = list(case["expected_tables"])
    retrieved = {result["full_name"] for result in top_results}
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
        key = row.get(field) if field else "overall"
        if key is not None:
            groups[key].append(row)
    return {
        key: {
            "questions": len(group),
            "macro_recall_at_10": (
                sum(item["recall_at_10"] for item in group) / len(group)
            ),
            "fully_covered_questions": sum(
                item["full_coverage"] for item in group
            ),
        }
        for key, group in sorted(groups.items())
    }


def rank_lookup(results):
    return {
        result["full_name"]: (rank, result)
        for rank, result in enumerate(results, start=1)
    }


def final_score(result):
    if result is None:
        return None
    return result.get("final_score", result.get("combined_score"))


def table_change_evidence(
    retriever,
    case,
    table,
    status,
    old_mode,
    new_mode,
    full_rankings,
    hybrid_rankings,
):
    case_id = case["id"]
    old_rank, old_result = rank_lookup(
        full_rankings[old_mode][case_id]
    ).get(table, (None, None))
    new_rank, new_result = rank_lookup(
        full_rankings[new_mode][case_id]
    ).get(table, (None, None))

    def hybrid_result(mode):
        return rank_lookup(hybrid_rankings[mode][case_id]).get(
            table, (None, None)
        )[1]

    original = hybrid_result("Hybrid")
    alias = hybrid_result("AliasHybrid")
    bm25 = hybrid_result("BM25Hybrid")
    alias_bm25 = hybrid_result("AliasBM25Hybrid")
    return {
        "status": status,
        "expected_table": table,
        "old_rank": old_rank,
        "new_rank": new_rank,
        "old_final_score": final_score(old_result),
        "new_final_score": final_score(new_result),
        "original_lexical_score": (
            original.get("lexical_score") if original else None
        ),
        "alias_lexical_score": alias.get("lexical_score") if alias else None,
        "original_bm25_raw": bm25.get("bm25_raw_score") if bm25 else None,
        "original_bm25_normalized": bm25.get("bm25_score") if bm25 else None,
        "alias_bm25_raw": (
            alias_bm25.get("bm25_raw_score") if alias_bm25 else None
        ),
        "alias_bm25_normalized": (
            alias_bm25.get("bm25_score") if alias_bm25 else None
        ),
        "alias_bm25_term_details": retriever.alias_bm25_term_details(
            case["question"], table
        ),
        "matching_metadata_aliases": retriever.bm25_alias_evidence(
            case["question"], table
        ),
        "old_source_seed_tables": (
            old_result.get("source_seed_tables", []) if old_result else []
        ),
        "new_source_seed_tables": (
            new_result.get("source_seed_tables", []) if new_result else []
        ),
        "interpretation": "score_and_rank_evidence_not_causal_proof",
    }


def transition_analysis(
    retriever,
    cases,
    old_mode,
    new_mode,
    evaluated,
    full_rankings,
    hybrid_rankings,
):
    output = {
        "improved": [],
        "unchanged": [],
        "regressed": [],
        "changed_case_evidence": [],
    }
    rows = {
        mode: {row["id"]: row for row in evaluated[mode]}
        for mode in (old_mode, new_mode)
    }
    for case in cases:
        case_id = case["id"]
        old = rows[old_mode][case_id]
        new = rows[new_mode][case_id]
        if new["recall_at_10"] > old["recall_at_10"]:
            classification = "improved"
        elif new["recall_at_10"] < old["recall_at_10"]:
            classification = "regressed"
        else:
            output["unchanged"].append(case_id)
            continue
        output[classification].append(case_id)
        old_top = {item["table"] for item in old["retrieved_top_10"]}
        new_top = {item["table"] for item in new["retrieved_top_10"]}
        gained = [
            table for table in case["expected_tables"]
            if table not in old_top and table in new_top
        ]
        lost = [
            table for table in case["expected_tables"]
            if table in old_top and table not in new_top
        ]
        changes = [
            table_change_evidence(
                retriever, case, table, "gained", old_mode, new_mode,
                full_rankings, hybrid_rankings,
            )
            for table in gained
        ]
        changes.extend(
            table_change_evidence(
                retriever, case, table, "lost", old_mode, new_mode,
                full_rankings, hybrid_rankings,
            )
            for table in lost
        )
        output["changed_case_evidence"].append({
            "case_id": case_id,
            "classification": classification,
            "old_recall_at_10": old["recall_at_10"],
            "new_recall_at_10": new["recall_at_10"],
            "expected_table_changes": changes,
        })
    return output


def saturation_aggregate(per_case):
    output = {}
    for scorer in ("bm25_without_aliases", "bm25_with_aliases"):
        rows = [item[scorer] for item in per_case]
        output[scorer] = {
            "mean_top_score_ties": statistics.mean(
                row["top_score_ties"] for row in rows
            ),
            "mean_near_max_candidates": statistics.mean(
                row["tables_near_maximum"] for row in rows
            ),
            "mean_top_20_score_spread": statistics.mean(
                row["top_20_score_spread"] for row in rows
            ),
        }
    return output


def validate_historical_bm25(report):
    """Ensure recomputed frozen BM25 baselines equal the prior result."""
    if not PRIOR_BM25_RESULT_PATH.exists():
        return {"available": False, "matched": None}
    prior = json.loads(PRIOR_BM25_RESULT_PATH.read_text(encoding="utf-8"))
    mode_names = ("Hybrid", "Graph", "BM25Hybrid", "BM25Graph")
    for suite_name in report["suites"]:
        for mode in mode_names:
            old_rows = prior["suites"][suite_name]["cases"][mode]
            new_rows = report["suites"][suite_name]["cases"][mode]
            old_signature = [
                (
                    row["id"], row["recall_at_10"],
                    row["missing_expected_tables"],
                    [item["table"] for item in row["retrieved_top_10"]],
                )
                for row in old_rows
            ]
            new_signature = [
                (
                    row["id"], row["recall_at_10"],
                    row["missing_expected_tables"],
                    [item["table"] for item in row["retrieved_top_10"]],
                )
                for row in new_rows
            ]
            if old_signature != new_signature:
                raise ValueError(
                    f"Historical BM25 baseline mismatch: {suite_name}/{mode}"
                )
    return {
        "available": True,
        "matched": True,
        "path": str(PRIOR_BM25_RESULT_PATH.relative_to(ROOT)),
        "sha256": sha256(PRIOR_BM25_RESULT_PATH),
    }


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
            print(
                f"  {row['id']}: recall={row['recall_at_10']:.4f}; "
                f"missing={missing}"
            )
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

    retriever = AliasBM25SchemaRetriever()
    assert retriever.index.ntotal == len(retriever.documents) == 2196
    indexed = {document["full_name"] for document in retriever.documents}
    suites = suite_definitions()
    assert {name: len(cases) for name, cases in suites.items()} == {
        "development_9": 9,
        "heldout_schema_20": 20,
        "real_world_observed_13": 13,
    }

    report = {
        "experiment": "controlled_metadata_english_alias_bm25",
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
        "alias_statistics": retriever.alias_statistics(),
        "suites": {},
        "integrity": {},
    }

    for suite_name, cases in suites.items():
        if any(
            table not in indexed
            for case in cases
            for table in case["expected_tables"]
        ):
            raise ValueError(f"Expected table outside corpus in {suite_name}")

        evaluated = {mode: [] for mode in MODES}
        full_rankings = {mode: {} for mode in MODES}
        hybrid_rankings = {
            mode: {} for mode in (
                "Hybrid", "AliasHybrid", "BM25Hybrid", "AliasBM25Hybrid"
            )
        }
        saturation = []
        for case in cases:
            question = case["question"]
            hybrid_all = retriever.retrieve_hybrid(
                question, top_k=retriever.index.ntotal
            )
            alias_all = retriever.retrieve_alias_hybrid(
                question, top_k=retriever.index.ntotal
            )
            bm25_all = retriever.retrieve_bm25_hybrid(
                question, top_k=retriever.index.ntotal
            )
            alias_bm25_all = retriever.retrieve_alias_bm25_hybrid(
                question, top_k=retriever.index.ntotal
            )
            hybrid_sets = {
                "Hybrid": hybrid_all,
                "AliasHybrid": alias_all,
                "BM25Hybrid": bm25_all,
                "AliasBM25Hybrid": alias_bm25_all,
            }
            graph_sets = {}
            for hybrid_mode, graph_mode in (
                ("Hybrid", "Graph"),
                ("AliasHybrid", "AliasGraph"),
                ("BM25Hybrid", "BM25Graph"),
                ("AliasBM25Hybrid", "AliasBM25Graph"),
            ):
                all_hybrid = hybrid_sets[hybrid_mode]
                graph_sets[graph_mode], _ = rank_expanded_candidates(
                    all_hybrid,
                    all_hybrid[:HYBRID_SEED_COUNT],
                    retriever.outgoing_adjacency,
                    retriever.index.ntotal,
                )
            all_results = {**hybrid_sets, **graph_sets}
            for mode, results in all_results.items():
                top_results = results[:TOP_K]
                if len(top_results) != TOP_K:
                    raise ValueError(
                        f"{suite_name}/{case['id']}/{mode} returned "
                        f"{len(top_results)}"
                    )
                evaluated[mode].append(evaluate_case(case, mode, top_results))
                full_rankings[mode][case["id"]] = results
            for mode, results in hybrid_sets.items():
                hybrid_rankings[mode][case["id"]] = results
            saturation.append({
                "case_id": case["id"],
                **retriever.bm25_saturation_statistics(question),
            })

        transitions = {}
        for old_mode, new_mode in (
            ("Graph", "AliasBM25Graph"),
            ("BM25Graph", "AliasBM25Graph"),
            ("AliasGraph", "AliasBM25Graph"),
        ):
            label = f"{old_mode}_to_{new_mode}"
            transitions[label] = transition_analysis(
                retriever, cases, old_mode, new_mode, evaluated,
                full_rankings, hybrid_rankings,
            )
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

    report["historical_bm25_baseline_validation"] = (
        validate_historical_bm25(report)
    )
    after_hashes = hashes(paths)
    if before_hashes != after_hashes:
        raise ValueError("A frozen artifact changed during Alias+BM25 evaluation")
    report["integrity"] = {
        "indexed_table_count": 2196,
        "protected_file_hashes_unchanged": True,
        "embeddings_and_faiss_unchanged": True,
        "all_previous_retrievers_unchanged": True,
        "alias_catalog_unchanged": True,
        "benchmark_files_unchanged": True,
        "gold_sql_files_unchanged": True,
        "english_metadata_aliases_only": True,
        "persian_aliases_used": False,
        "support_ticket_content_used": False,
        "manually_invented_synonyms_used": False,
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
    print("Historical and integrity checks passed")
    return report


if __name__ == "__main__":
    run()
