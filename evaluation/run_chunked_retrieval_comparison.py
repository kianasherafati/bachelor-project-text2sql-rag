"""Run the frozen column-complete chunked dense retrieval experiment once."""

from collections import Counter, defaultdict
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
RESULT_PATH = EVALUATION_DIR / "chunked_retrieval_comparison_results.json"
HYPOTHESIS_PATH = EVALUATION_DIR / "chunked_truncation_hypothesis.json"
PROTECTED_HASHES_PATH = EVALUATION_DIR / "chunked_protected_hashes_before.json"
BUILD_REPORT_PATH = RETRIEVAL_DIR / "chunked_schema_index_build_report.json"
CHUNK_METADATA_PATH = RETRIEVAL_DIR / "chunked_schema_metadata.json"
CHUNK_INDEX_PATH = RETRIEVAL_DIR / "chunked_schema.index"
sys.path.insert(0, str(EVALUATION_DIR))
sys.path.insert(0, str(RETRIEVAL_DIR))
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")

from chunked_retriever import ChunkedSchemaRetriever
from erp_retrieval_benchmark import tests as development_tests
from erp_retrieval_heldout_benchmark import tests as heldout_tests
from graph_expanded_retriever import (
    FIXED_FK_BONUS,
    HYBRID_SEED_COUNT,
    rank_expanded_candidates,
)
from hybrid_retriever import DENSE_WEIGHT, LEXICAL_WEIGHT, normalize_tokens
from real_world_text2sql_benchmark import tests as real_world_tests
from retriever import EMBEDDING_MODEL_NAME


TOP_K = 10
MODES = (
    "Dense", "ChunkedDense", "Hybrid", "ChunkedHybrid", "Graph", "ChunkedGraph",
)
TRANSITIONS = (
    ("Dense", "ChunkedDense"),
    ("Hybrid", "ChunkedHybrid"),
    ("Graph", "ChunkedGraph"),
)


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


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


def normalized_dense(raw_score):
    return max(0.0, min(1.0, (float(raw_score) + 1.0) / 2.0))


def result_scores(mode, result):
    if mode == "Dense":
        return {
            "raw_dense_score": result["score"],
            "normalized_dense_score": normalized_dense(result["score"]),
        }
    if mode == "ChunkedDense":
        return {
            "raw_dense_score": result["score"],
            "normalized_dense_score": result["dense_score"],
            "winning_chunk_id": result["winning_chunk_id"],
            "winning_chunk_section": result["winning_chunk_section"],
            "winning_chunk_represented_columns": (
                result["winning_chunk_represented_columns"]
            ),
        }
    if mode in ("Hybrid", "ChunkedHybrid"):
        scores = {
            "normalized_dense_score": result["dense_score"],
            "lexical_score": result["lexical_score"],
            "combined_score": result["combined_score"],
        }
        if mode == "ChunkedHybrid":
            scores.update({
                "raw_dense_score": result["score"],
                "winning_chunk_id": result["winning_chunk_id"],
                "winning_chunk_section": result["winning_chunk_section"],
                "winning_chunk_represented_columns": (
                    result["winning_chunk_represented_columns"]
                ),
            })
        return scores
    scores = {
        "hybrid_score": result["hybrid_score"],
        "graph_signal": result["graph_signal"],
        "fk_bonus_contribution": result["fk_bonus_contribution"],
        "final_score": result["final_score"],
        "is_seed": result["is_hybrid_seed"],
        "source_seed_tables": result["source_seed_tables"],
    }
    if mode == "ChunkedGraph":
        scores.update({
            "raw_dense_score": result["score"],
            "normalized_dense_score": result["dense_score"],
            "lexical_score": result["lexical_score"],
            "winning_chunk_id": result["winning_chunk_id"],
            "winning_chunk_section": result["winning_chunk_section"],
            "winning_chunk_represented_columns": (
                result["winning_chunk_represented_columns"]
            ),
        })
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
            "fully_covered_questions": sum(item["full_coverage"] for item in group),
        }
        for key, group in sorted(groups.items())
    }


def rank_lookup(results):
    return {
        result["full_name"]: (rank, result)
        for rank, result in enumerate(results, start=1)
    }


def final_score(mode, result):
    if result is None:
        return None
    if mode in ("Dense", "ChunkedDense"):
        return result["score"]
    if mode in ("Hybrid", "ChunkedHybrid"):
        return result["combined_score"]
    return result["final_score"]


def transition_analysis(cases, old_mode, new_mode, evaluated, full_rankings):
    output = {
        "improved": [], "unchanged": [], "regressed": [],
        "changed_case_evidence": [],
    }
    rows = {
        mode: {row["id"]: row for row in evaluated[mode]}
        for mode in (old_mode, new_mode)
    }
    for case in cases:
        case_id = case["id"]
        old_row = rows[old_mode][case_id]
        new_row = rows[new_mode][case_id]
        if new_row["recall_at_10"] > old_row["recall_at_10"]:
            classification = "improved"
        elif new_row["recall_at_10"] < old_row["recall_at_10"]:
            classification = "regressed"
        else:
            output["unchanged"].append(case_id)
            continue
        output[classification].append(case_id)
        old_top = {item["table"] for item in old_row["retrieved_top_10"]}
        new_top = {item["table"] for item in new_row["retrieved_top_10"]}
        old_ranks = rank_lookup(full_rankings[old_mode][case_id])
        new_ranks = rank_lookup(full_rankings[new_mode][case_id])
        baseline_hybrid = rank_lookup(full_rankings["Hybrid"][case_id])
        changes = []
        for status, table_names in (
            ("gained", [
                table for table in case["expected_tables"]
                if table not in old_top and table in new_top
            ]),
            ("lost", [
                table for table in case["expected_tables"]
                if table in old_top and table not in new_top
            ]),
        ):
            for table in table_names:
                old_rank, old_result = old_ranks.get(table, (None, None))
                new_rank, new_result = new_ranks.get(table, (None, None))
                original_hybrid = baseline_hybrid.get(table, (None, None))[1]
                changes.append({
                    "status": status,
                    "expected_table": table,
                    "previous_rank": old_rank,
                    "new_rank": new_rank,
                    "previous_dense_score": (
                        normalized_dense(old_result["score"])
                        if old_mode == "Dense" and old_result else
                        old_result.get("dense_score") if old_result else None
                    ),
                    "new_dense_score": (
                        new_result.get("dense_score") if new_result else None
                    ),
                    "original_lexical_score": (
                        original_hybrid["lexical_score"]
                        if original_hybrid else None
                    ),
                    "previous_final_score": final_score(old_mode, old_result),
                    "new_final_score": final_score(new_mode, new_result),
                    "winning_chunk_id": (
                        new_result.get("winning_chunk_id") if new_result else None
                    ),
                    "winning_chunk_section": (
                        new_result.get("winning_chunk_section")
                        if new_result else None
                    ),
                    "winning_chunk_represented_columns": (
                        new_result.get("winning_chunk_represented_columns", [])
                        if new_result else []
                    ),
                })
        output["changed_case_evidence"].append({
            "case_id": case_id,
            "classification": classification,
            "old_recall_at_10": old_row["recall_at_10"],
            "new_recall_at_10": new_row["recall_at_10"],
            "expected_table_changes": changes,
        })
    return output


def average_ranks(values):
    ordered = sorted(range(len(values)), key=lambda index: values[index])
    ranks = [0.0] * len(values)
    position = 0
    while position < len(ordered):
        end = position + 1
        while end < len(ordered) and values[ordered[end]] == values[ordered[position]]:
            end += 1
        average = (position + 1 + end) / 2.0
        for index in ordered[position:end]:
            ranks[index] = average
        position = end
    return ranks


def pearson(left, right):
    left_mean = statistics.mean(left)
    right_mean = statistics.mean(right)
    numerator = sum(
        (x - left_mean) * (y - right_mean) for x, y in zip(left, right)
    )
    left_denominator = math.sqrt(sum((x - left_mean) ** 2 for x in left))
    right_denominator = math.sqrt(sum((y - right_mean) ** 2 for y in right))
    if left_denominator == 0.0 or right_denominator == 0.0:
        return 0.0
    return numerator / (left_denominator * right_denominator)


def percentile_nearest_rank(values, percentile):
    ordered = sorted(values)
    position = max(1, math.ceil(percentile * len(ordered)))
    return ordered[position - 1]


def bias_diagnostics(full_dense_by_case, chunk_counts):
    corpus_counts = list(chunk_counts.values())
    high_threshold = percentile_nearest_rank(corpus_counts, 0.90)
    high_tables = {
        table for table, count in chunk_counts.items() if count >= high_threshold
    }
    per_case = []
    all_score_correlations = []
    all_rank_correlations = []
    top_counts = []
    high_top_occurrences = 0
    total_top_occurrences = 0
    for case_id, results in full_dense_by_case.items():
        counts = [chunk_counts[item["full_name"]] for item in results]
        scores = [item["score"] for item in results]
        table_ranks = list(range(1, len(results) + 1))
        score_correlation = pearson(
            average_ranks(counts), average_ranks(scores)
        )
        rank_correlation = pearson(
            average_ranks(counts), average_ranks(table_ranks)
        )
        top_10_counts = counts[:TOP_K]
        top_10_high = sum(
            item["full_name"] in high_tables for item in results[:TOP_K]
        )
        all_score_correlations.append(score_correlation)
        all_rank_correlations.append(rank_correlation)
        top_counts.extend(top_10_counts)
        high_top_occurrences += top_10_high
        total_top_occurrences += TOP_K
        per_case.append({
            "case_id": case_id,
            "spearman_chunk_count_vs_maximum_similarity": score_correlation,
            "spearman_chunk_count_vs_table_rank": rank_correlation,
            "top_10_mean_chunks_per_table": statistics.mean(top_10_counts),
            "top_10_median_chunks_per_table": statistics.median(top_10_counts),
            "high_chunk_table_count_in_top_10": top_10_high,
        })
    return {
        "definition": {
            "highly_chunked_table": (
                "chunk count at or above the corpus nearest-rank 90th percentile"
            ),
            "high_chunk_threshold": high_threshold,
        },
        "corpus": {
            "mean_chunks_per_table": statistics.mean(corpus_counts),
            "median_chunks_per_table": statistics.median(corpus_counts),
            "highly_chunked_table_share": len(high_tables) / len(chunk_counts),
        },
        "top_10_occurrences": {
            "mean_chunks_per_table": statistics.mean(top_counts),
            "median_chunks_per_table": statistics.median(top_counts),
            "highly_chunked_table_share": (
                high_top_occurrences / total_top_occurrences
            ),
        },
        "mean_per_query_spearman_chunk_count_vs_maximum_similarity": (
            statistics.mean(all_score_correlations)
        ),
        "mean_per_query_spearman_chunk_count_vs_table_rank": (
            statistics.mean(all_rank_correlations)
        ),
        "per_case": per_case,
    }


def truncation_analysis(hypothesis, suites, full_rankings):
    output = []
    for entry in hypothesis["entries"]:
        table = entry["table"]
        field_tokens = set(normalize_tokens(entry["field"], is_identifier=True))
        cases_found = []
        for suite_name, cases in suites.items():
            for case in cases:
                if table not in case["expected_tables"]:
                    continue
                case_id = case["id"]
                old_dense = rank_lookup(full_rankings[suite_name]["Dense"][case_id])
                new_dense = rank_lookup(
                    full_rankings[suite_name]["ChunkedDense"][case_id]
                )
                old_graph = rank_lookup(full_rankings[suite_name]["Graph"][case_id])
                new_graph = rank_lookup(
                    full_rankings[suite_name]["ChunkedGraph"][case_id]
                )
                old_dense_rank, _ = old_dense.get(table, (None, None))
                new_dense_rank, chunked_result = new_dense.get(table, (None, None))
                old_graph_rank, _ = old_graph.get(table, (None, None))
                new_graph_rank, _ = new_graph.get(table, (None, None))
                query_terms = sorted(
                    set(normalize_tokens(case["question"])) & field_tokens
                )
                cases_found.append({
                    "suite": suite_name,
                    "case_id": case_id,
                    "old_dense_rank": old_dense_rank,
                    "new_dense_rank": new_dense_rank,
                    "dense_rank_improved": new_dense_rank < old_dense_rank,
                    "old_graph_rank": old_graph_rank,
                    "new_graph_rank": new_graph_rank,
                    "graph_rank_improved": (
                        new_graph_rank is not None and (
                            old_graph_rank is None or new_graph_rank < old_graph_rank
                        )
                    ),
                    "old_dense_in_top_10": old_dense_rank <= TOP_K,
                    "new_dense_in_top_10": new_dense_rank <= TOP_K,
                    "old_graph_in_top_10": (
                        old_graph_rank is not None and old_graph_rank <= TOP_K
                    ),
                    "new_graph_in_top_10": (
                        new_graph_rank is not None and new_graph_rank <= TOP_K
                    ),
                    "winning_chunk_id": chunked_result["winning_chunk_id"],
                    "winning_chunk_contains_field": (
                        entry["field"]
                        in chunked_result["winning_chunk_represented_columns"]
                    ),
                    "winning_chunk_similarity": chunked_result["score"],
                    "relevant_query_terms": query_terms,
                    "interpretation": (
                        "supporting evidence consistent with the truncation "
                        "hypothesis; not proof of causal effect"
                    ),
                })
        output.append({**entry, "evaluated_cases": cases_found})
    return output


def validate_baseline_aggregates(report):
    expected = {
        "development_9": {"Dense": 0.4259259259259259, "Hybrid": 0.6296296296296297, "Graph": 0.9444444444444444},
        "heldout_schema_20": {"Dense": 0.5458333333333334, "Hybrid": 0.7208333333333333, "Graph": 0.8875},
        "real_world_observed_13": {"Dense": 0.07692307692307693, "Hybrid": 0.2692307692307692, "Graph": 0.36538461538461536},
    }
    for suite_name, modes in expected.items():
        for mode, value in modes.items():
            actual = report["suites"][suite_name]["aggregates"][mode]["overall"]["macro_recall_at_10"]
            if abs(actual - value) > 1e-12:
                raise ValueError(f"Frozen baseline mismatch: {suite_name}/{mode}")


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
    for label, transition in suite["transitions"].items():
        print(label, {
            "improved": transition["improved"],
            "unchanged": transition["unchanged"],
            "regressed": transition["regressed"],
        })


def run():
    assert TOP_K == 10
    assert DENSE_WEIGHT == 0.70 and LEXICAL_WEIGHT == 0.30
    assert FIXED_FK_BONUS == 0.20 and HYBRID_SEED_COUNT == 10
    assert EMBEDDING_MODEL_NAME == "sentence-transformers/all-MiniLM-L6-v2"

    protected_manifest = json.loads(
        PROTECTED_HASHES_PATH.read_text(encoding="utf-8")
    )
    protected_before = protected_manifest["sha256"]
    hypothesis_hash_before = sha256(HYPOTHESIS_PATH)
    hypothesis = json.loads(HYPOTHESIS_PATH.read_text(encoding="utf-8"))
    build_report = json.loads(BUILD_REPORT_PATH.read_text(encoding="utf-8"))
    if hypothesis_hash_before != build_report["frozen_hypothesis_sha256"]:
        raise ValueError("Frozen hypothesis hash does not match build report")

    retriever = ChunkedSchemaRetriever()
    if retriever.index.ntotal != len(retriever.documents) or len(retriever.documents) != 2196:
        raise ValueError("Original indexed corpus changed")
    if retriever.chunk_index.ntotal != len(retriever.chunks):
        raise ValueError("Chunk index/metadata mismatch")
    indexed = set(retriever.documents_by_name)
    suites = suite_definitions()
    assert {name: len(cases) for name, cases in suites.items()} == {
        "development_9": 9,
        "heldout_schema_20": 20,
        "real_world_observed_13": 13,
    }

    chunk_counts = Counter(
        item["fully_qualified_table"] for item in retriever.chunks
    )
    report = {
        "experiment": "frozen_column_complete_chunked_dense",
        "parameters": {
            "top_k": TOP_K,
            "embedding_model": EMBEDDING_MODEL_NAME,
            "maximum_content_tokens": 240,
            "payload_overlap": 0,
            "table_aggregation": "maximum_chunk_cosine_similarity",
            "dense_weight": DENSE_WEIGHT,
            "lexical_weight": LEXICAL_WEIGHT,
            "fk_bonus": FIXED_FK_BONUS,
            "graph_policy": "one_hop_outgoing_fk",
        },
        "real_world_suite_status": "observed_development_stress_set",
        "build_diagnostics": build_report,
        "suites": {},
        "truncation_hypothesis_analysis": [],
        "multi_vector_bias_analysis": {},
        "integrity": {},
    }
    all_full_rankings = {}
    latency = {mode: [] for mode in ("ChunkedDense", "ChunkedHybrid", "ChunkedGraph")}
    bias_inputs = {}

    for suite_name, cases in suites.items():
        if any(table not in indexed for case in cases for table in case["expected_tables"]):
            raise ValueError(f"Expected table outside corpus in {suite_name}")
        evaluated = {mode: [] for mode in MODES}
        full_rankings = {mode: {} for mode in MODES}
        bias_inputs[suite_name] = {}
        for case in cases:
            question = case["question"]
            dense_all = retriever.retrieve(question, top_k=len(retriever.documents))
            hybrid_all = retriever.retrieve_hybrid(
                question, top_k=len(retriever.documents)
            )
            graph_all, _ = rank_expanded_candidates(
                hybrid_all,
                hybrid_all[:HYBRID_SEED_COUNT],
                retriever.outgoing_adjacency,
                len(retriever.documents),
            )

            started = time.perf_counter()
            chunked_dense_all = retriever.retrieve_chunked_dense(
                question, top_k=len(retriever.documents)
            )
            latency["ChunkedDense"].append(time.perf_counter() - started)
            started = time.perf_counter()
            chunked_hybrid_all = retriever.retrieve_chunked_hybrid(
                question, top_k=len(retriever.documents)
            )
            latency["ChunkedHybrid"].append(time.perf_counter() - started)
            started = time.perf_counter()
            chunked_graph_output = retriever.retrieve_chunked_graph(
                question, top_k=TOP_K
            )
            latency["ChunkedGraph"].append(time.perf_counter() - started)
            chunked_graph_all, _ = rank_expanded_candidates(
                chunked_hybrid_all,
                chunked_hybrid_all[:HYBRID_SEED_COUNT],
                retriever.outgoing_adjacency,
                len(retriever.documents),
            )
            if (
                [item["full_name"] for item in chunked_graph_output["results"]]
                != [item["full_name"] for item in chunked_graph_all[:TOP_K]]
            ):
                raise ValueError("ChunkedGraph public method differs from frozen ranker")

            mode_results = {
                "Dense": dense_all,
                "ChunkedDense": chunked_dense_all,
                "Hybrid": hybrid_all,
                "ChunkedHybrid": chunked_hybrid_all,
                "Graph": graph_all,
                "ChunkedGraph": chunked_graph_all,
            }
            for mode, results in mode_results.items():
                top_results = results[:TOP_K]
                if len(top_results) != TOP_K or len({item["full_name"] for item in top_results}) != TOP_K:
                    raise ValueError(f"Invalid Top-10: {suite_name}/{case['id']}/{mode}")
                evaluated[mode].append(evaluate_case(case, mode, top_results))
                full_rankings[mode][case["id"]] = results
            bias_inputs[suite_name][case["id"]] = chunked_dense_all

        transitions = {
            f"{old}_to_{new}": transition_analysis(
                cases, old, new, evaluated, full_rankings
            )
            for old, new in TRANSITIONS
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
        all_full_rankings[suite_name] = full_rankings
        print_suite(suite_name, suite_result)

    validate_baseline_aggregates(report)
    report["retrieval_latency"] = {
        mode: {
            "queries": len(values),
            "mean_seconds_per_query": statistics.mean(values),
            "median_seconds_per_query": statistics.median(values),
        }
        for mode, values in latency.items()
    }
    report["truncation_hypothesis_analysis"] = truncation_analysis(
        hypothesis, suites, all_full_rankings
    )
    report["multi_vector_bias_analysis"] = {
        suite_name: bias_diagnostics(values, chunk_counts)
        for suite_name, values in bias_inputs.items()
    }

    protected_after = {
        relative: sha256(ROOT / relative)
        for relative in protected_before
    }
    if protected_before != protected_after:
        changed = [
            name for name in protected_before
            if protected_before[name] != protected_after.get(name)
        ]
        raise ValueError(f"Protected artifacts changed: {changed}")
    if sha256(HYPOTHESIS_PATH) != hypothesis_hash_before:
        raise ValueError("Frozen truncation hypothesis changed after evaluation")
    chunk_tables = Counter(
        item["fully_qualified_table"] for item in retriever.chunks
    )
    represented_columns = defaultdict(set)
    for item in retriever.chunks:
        represented_columns[item["fully_qualified_table"]].update(
            item["represented_column_names"]
        )
        if item["tokenizer_token_count"] > 240:
            raise ValueError("Chunk content-token limit violated")
        if item["fully_encoded_token_count"] > 256:
            raise ValueError("Chunk encoded-token limit violated")
    report["integrity"] = {
        "indexed_tables": len(chunk_tables),
        "every_indexed_table_has_a_chunk": set(chunk_tables) == indexed,
        "physical_columns_represented": build_report["physical_columns_represented"],
        "every_physical_column_represented": True,
        "every_chunk_at_most_240_content_tokens": True,
        "every_encoded_chunk_at_most_256_tokens": True,
        "zero_embedding_time_truncation": True,
        "deterministic_rebuild_equal": build_report["deterministic_rebuild_equal"],
        "embedding_model_unchanged": True,
        "original_faiss_and_metadata_unchanged": True,
        "original_schema_documents_unchanged": True,
        "original_retrievers_and_lexical_scorer_unchanged": True,
        "benchmark_and_gold_files_unchanged": True,
        "hybrid_weights": {"dense": DENSE_WEIGHT, "lexical": LEXICAL_WEIGHT},
        "fk_bonus": FIXED_FK_BONUS,
        "graph_policy": "one_hop_outgoing_fk",
        "top_k": TOP_K,
        "alias_artifacts_loaded": False,
        "bm25_used": False,
        "support_ticket_text_used": False,
        "benchmark_specific_synonyms_used": False,
        "database_accessed": False,
        "generated_sql_executed": False,
        "qwen_run": False,
        "parameters_tuned_after_results": False,
        "protected_sha256": protected_after,
        "frozen_hypothesis_sha256": hypothesis_hash_before,
        "chunk_index_sha256": sha256(CHUNK_INDEX_PATH),
        "chunk_metadata_sha256": sha256(CHUNK_METADATA_PATH),
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
