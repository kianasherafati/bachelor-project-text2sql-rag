"""Analyze oracle candidate coverage from already-saved retrieval results only."""

from __future__ import annotations

from collections import defaultdict
import hashlib
import json
from pathlib import Path
import statistics


ROOT = Path(__file__).resolve().parents[1]
EVALUATION_DIR = ROOT / "evaluation"
SOURCE_PATH = EVALUATION_DIR / "bge_m3_retrieval_comparison_results.json"
OUTPUT_PATH = EVALUATION_DIR / "reranker_candidate_coverage_results.json"

DEPTHS = (10, 20, 50, 100, 200)
SYSTEMS = (
    "MiniLM Dense",
    "MiniLM Hybrid",
    "MiniLM Graph",
    "BGE-Dense",
    "BGE-Hybrid",
    "BGE-Graph",
)
UNIONS = {
    "BGE-Dense + MiniLM Graph": ("BGE-Dense", "MiniLM Graph"),
    "BGE-Dense + MiniLM Hybrid": ("BGE-Dense", "MiniLM Hybrid"),
    "BGE-Dense + MiniLM Graph + MiniLM Hybrid": (
        "BGE-Dense",
        "MiniLM Graph",
        "MiniLM Hybrid",
    ),
}
SUITE_LABELS = {
    "development_9": "Development 9",
    "heldout_schema_20": "Held-out schema 20",
    "real_world_observed_13": "Observed real-world development/stress 13",
}
CORPUS_SIZE = 2196


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_source():
    payload = json.loads(SOURCE_PATH.read_text(encoding="utf-8"))
    actual = tuple(payload["suites"]["development_9"]["per_system"])
    if set(actual) != set(SYSTEMS):
        raise ValueError(f"Unexpected frozen systems: {actual}")
    return payload


def case_definitions(payload, suite_name):
    return payload["suites"][suite_name]["per_system"]["BGE-Dense"]


def expected_ranks(payload, suite_name, case_id):
    return {
        row["expected_table"]: {
            system: row[system]["rank"]
            for system in SYSTEMS
        }
        for row in payload["full_expected_table_diagnostics"][suite_name][case_id]
    }


def rank_is_covered(rank, depth):
    return rank is not None and rank <= depth


def summarize_membership(cases, membership):
    per_case = []
    absent_occurrences = 0
    for case in cases:
        covered = [
            table for table in case["expected_tables"]
            if membership(case["id"], table)
        ]
        missing = [
            table for table in case["expected_tables"]
            if table not in covered
        ]
        absent_occurrences += len(missing)
        per_case.append({
            "id": case["id"],
            "expected_table_count": len(case["expected_tables"]),
            "covered_expected_tables": covered,
            "missing_expected_tables": missing,
            "candidate_recall": len(covered) / len(case["expected_tables"]),
            "full_expected_coverage": not missing,
            "at_least_one_expected_table": bool(covered),
        })
    return {
        "macro_expected_table_candidate_recall": statistics.mean(
            row["candidate_recall"] for row in per_case
        ),
        "questions_with_every_expected_table": sum(
            row["full_expected_coverage"] for row in per_case
        ),
        "questions_with_at_least_one_expected_table": sum(
            row["at_least_one_expected_table"] for row in per_case
        ),
        "expected_table_occurrences_absent": absent_occurrences,
        "expected_table_occurrences_total": sum(
            len(case["expected_tables"]) for case in cases
        ),
        "per_case": per_case,
    }


def top_10_sets(payload, suite_name, system):
    return {
        row["id"]: {item["table"] for item in row["retrieved_top_10"]}
        for row in payload["suites"][suite_name]["per_system"][system]
    }


def candidate_count_summary(payload, suite_name, cases, sources, depth):
    if depth == 10:
        by_source = {
            source: top_10_sets(payload, suite_name, source)
            for source in sources
        }
        counts = {
            case["id"]: len(set().union(*(
                by_source[source][case["id"]] for source in sources
            )))
            for case in cases
        }
        values = list(counts.values())
        return {
            "exact_unique_counts_available": True,
            "per_case_unique_candidate_count": counts,
            "minimum_unique_candidates": min(values),
            "mean_unique_candidates": statistics.mean(values),
            "median_unique_candidates": statistics.median(values),
            "maximum_unique_candidates": max(values),
            "table_question_pairs": sum(values),
        }
    source_slots = min(CORPUS_SIZE, depth) * len(sources)
    return {
        "exact_unique_counts_available": False,
        "reason": (
            "The frozen artifact retained complete ranks only for expected tables "
            "and complete candidate identities only for Top 10."
        ),
        "per_question_unique_candidate_count_lower_bound": depth,
        "per_question_unique_candidate_count_upper_bound": min(
            CORPUS_SIZE, source_slots
        ),
        "source_slots_before_deduplication_per_question": source_slots,
        "table_question_pair_lower_bound": len(cases) * depth,
        "table_question_pair_upper_bound": (
            len(cases) * min(CORPUS_SIZE, source_slots)
        ),
    }


def descriptive_class(rank):
    if rank is None or rank > 200:
        return "absent beyond 200"
    if rank <= 20:
        return "easy candidate"
    if rank <= 50:
        return "moderate candidate"
    if rank <= 100:
        return "broad candidate"
    return "very broad candidate"


def analyze_suite(payload, suite_name):
    cases = case_definitions(payload, suite_name)
    ranks = {
        case["id"]: expected_ranks(payload, suite_name, case["id"])
        for case in cases
    }
    single = {}
    for system in SYSTEMS:
        single[system] = {}
        for depth in DEPTHS:
            single[system][str(depth)] = summarize_membership(
                cases,
                lambda case_id, table, s=system, n=depth: rank_is_covered(
                    ranks[case_id][table][s], n
                ),
            )

    unions = {}
    for union_name, sources in UNIONS.items():
        unions[union_name] = {}
        for depth in DEPTHS:
            coverage = summarize_membership(
                cases,
                lambda case_id, table, ss=sources, n=depth: any(
                    rank_is_covered(ranks[case_id][table][source], n)
                    for source in ss
                ),
            )
            coverage["candidate_count"] = candidate_count_summary(
                payload, suite_name, cases, sources, depth
            )
            coverage["sources"] = list(sources)
            coverage["depth_per_source"] = depth
            unions[union_name][str(depth)] = coverage

    return {
        "label": SUITE_LABELS[suite_name],
        "question_count": len(cases),
        "expected_table_occurrences": sum(
            len(case["expected_tables"]) for case in cases
        ),
        "per_case_expected_table_ranks": ranks,
        "single_system_coverage": single,
        "union_coverage": unions,
    }


def real_world_rank_analysis(suite_result):
    output = []
    for case_id, tables in suite_result["per_case_expected_table_ranks"].items():
        for table, ranks in tables.items():
            finite = [rank for rank in ranks.values() if rank is not None]
            best_rank = min(finite) if finite else None
            output.append({
                "case_id": case_id,
                "expected_table": table,
                "ranks": ranks,
                "classification_by_system": {
                    system: descriptive_class(rank)
                    for system, rank in ranks.items()
                },
                "best_rank_across_required_systems": best_rank,
                "best_available_classification": descriptive_class(best_rank),
                "best_sources": [
                    system for system, rank in ranks.items()
                    if rank == best_rank
                ] if best_rank is not None else [],
            })
    return output


def cost_analysis(suite_results):
    suite_counts = {
        suite: result["question_count"]
        for suite, result in suite_results.items()
    }
    suite_counts["combined_42"] = sum(suite_counts.values())
    single = {
        str(depth): {
            suite: questions * depth
            for suite, questions in suite_counts.items()
        }
        for depth in DEPTHS
    }
    unions = {}
    for name, sources in UNIONS.items():
        unions[name] = {}
        for depth in DEPTHS:
            if depth == 10:
                per_suite = {
                    suite: suite_results[suite]["union_coverage"][name]["10"]
                    ["candidate_count"]["table_question_pairs"]
                    for suite in suite_results
                }
                per_suite["combined_42"] = sum(per_suite.values())
                unions[name]["10"] = {
                    "exact_table_question_pairs_after_deduplication": per_suite
                }
            else:
                upper_per_question = min(CORPUS_SIZE, depth * len(sources))
                unions[name][str(depth)] = {
                    "table_question_pair_bounds_after_deduplication": {
                        suite: {
                            "lower": questions * depth,
                            "upper": questions * upper_per_question,
                        }
                        for suite, questions in suite_counts.items()
                    },
                    "source_slots_before_deduplication_per_question": (
                        depth * len(sources)
                    ),
                }
    return {
        "single_system_exact_table_question_pairs": single,
        "union_table_question_pairs": unions,
    }


def compact_coverage(data):
    return {
        "macro_expected_table_candidate_recall": data[
            "macro_expected_table_candidate_recall"
        ],
        "questions_with_every_expected_table": data[
            "questions_with_every_expected_table"
        ],
        "questions_with_at_least_one_expected_table": data[
            "questions_with_at_least_one_expected_table"
        ],
        "expected_table_occurrences_absent": data[
            "expected_table_occurrences_absent"
        ],
    }


def fair_size_comparisons(suite_results):
    comparisons = {}
    for suite_name, suite in suite_results.items():
        comparisons[suite_name] = {
            "up_to_50_candidates": {
                "BGE-Dense Top-50 (exactly 50)": compact_coverage(
                    suite["single_system_coverage"]["BGE-Dense"]["50"]
                ),
                "BGE-Dense Top-20 + MiniLM Graph Top-20 (20-40 unique)": (
                    compact_coverage(
                        suite["union_coverage"]["BGE-Dense + MiniLM Graph"]["20"]
                    )
                ),
            },
            "up_to_100_candidates": {
                "BGE-Dense Top-100 (exactly 100)": compact_coverage(
                    suite["single_system_coverage"]["BGE-Dense"]["100"]
                ),
                "BGE-Dense Top-50 + MiniLM Graph Top-50 (50-100 unique)": (
                    compact_coverage(
                        suite["union_coverage"]["BGE-Dense + MiniLM Graph"]["50"]
                    )
                ),
            },
        }
    return comparisons


def recommendation(suite_results):
    union_name = "BGE-Dense + MiniLM Graph"
    depth = "50"
    top_10_counts = [
        suite["union_coverage"][union_name]["10"]["candidate_count"]
        ["table_question_pairs"]
        for suite in suite_results.values()
    ]
    observed_unique_ratio = sum(top_10_counts) / (42 * 20)
    estimated_unique = observed_unique_ratio * 100
    coverage = {
        suite_name: compact_coverage(
            suite["union_coverage"][union_name][depth]
        )
        for suite_name, suite in suite_results.items()
    }
    missing = {
        suite_name: {
            row["id"]: row["missing_expected_tables"]
            for row in suite["union_coverage"][union_name][depth]["per_case"]
            if row["missing_expected_tables"]
        }
        for suite_name, suite in suite_results.items()
    }
    return {
        "recommended_frozen_candidate_pool": (
            "BGE-Dense Top-50 union MiniLM Graph Top-50"
        ),
        "candidate_sources": ["BGE-Dense", "MiniLM Graph"],
        "fixed_depth_from_each_source": 50,
        "deduplication_rule": "fully-qualified table name",
        "candidate_order_before_reranking": (
            "candidate set only; retain both source ranks as provenance"
        ),
        "unique_candidate_count": {
            "hard_lower_bound_per_question": 50,
            "hard_upper_bound_per_question": 100,
            "estimated_mean_from_observed_top_10_overlap": estimated_unique,
            "estimate_basis": {
                "exact_unique_candidates_across_all_42_top_10_unions": sum(
                    top_10_counts
                ),
                "source_slots_across_all_42_top_10_unions": 42 * 20,
                "observed_unique_fraction": observed_unique_ratio,
                "warning": (
                    "This estimate is descriptive; exact Top-50 identities were "
                    "not persisted and retrieval was not rerun."
                ),
            },
        },
        "maximum_table_question_pairs": {
            "development_9": 900,
            "heldout_schema_20": 2000,
            "real_world_observed_13": 1300,
            "combined_42": 4200,
        },
        "candidate_coverage": coverage,
        "remaining_unreachable_expected_tables_at_this_pool": missing,
        "selection_basis": (
            "One uniform predeclared depth for both sources; selected from aggregate "
            "coverage and maximum cost, without per-case or asymmetric depth tuning."
        ),
    }


def validate(result):
    expected_sizes = {
        "development_9": 9,
        "heldout_schema_20": 20,
        "real_world_observed_13": 13,
    }
    assert {
        name: suite["question_count"]
        for name, suite in result["suites"].items()
    } == expected_sizes
    for suite in result["suites"].values():
        for system in SYSTEMS:
            assert set(suite["single_system_coverage"][system]) == {
                str(depth) for depth in DEPTHS
            }
        for union in UNIONS:
            assert set(suite["union_coverage"][union]) == {
                str(depth) for depth in DEPTHS
            }


def main():
    source_hash_before = sha256_file(SOURCE_PATH)
    payload = load_source()
    suites = {
        suite_name: analyze_suite(payload, suite_name)
        for suite_name in SUITE_LABELS
    }
    result = {
        "analysis": "frozen retrieval candidate recall / oracle coverage",
        "source_artifact": str(SOURCE_PATH.relative_to(ROOT)),
        "source_sha256": source_hash_before,
        "candidate_depths": list(DEPTHS),
        "systems": list(SYSTEMS),
        "unions": {name: list(sources) for name, sources in UNIONS.items()},
        "method": {
            "retrieval_executed": False,
            "coverage_rule": "expected table rank <= candidate depth",
            "union_rule": "Top-N membership from any source, deduplicated by fully-qualified table",
            "real_c04_not_limited_by_final_top_10": True,
            "full_candidate_identities_available_through_depth": 10,
            "deeper_union_unique_counts": (
                "reported as bounds because non-expected candidate identities "
                "beyond rank 10 were not persisted"
            ),
        },
        "suites": suites,
        "real_world_expected_table_rank_analysis": real_world_rank_analysis(
            suites["real_world_observed_13"]
        ),
        "candidate_set_cost": cost_analysis(suites),
        "fair_size_matched_comparisons": fair_size_comparisons(suites),
        "recommendation": recommendation(suites),
        "integrity": {
            "source_artifact_unchanged": sha256_file(SOURCE_PATH) == source_hash_before,
            "retrieval_rerun": False,
            "reranker_run": False,
            "database_accessed": False,
            "qwen_run": False,
            "support_tickets_accessed": False,
            "retrieval_parameters_changed": False,
        },
    }
    validate(result)
    OUTPUT_PATH.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        suite_name: {
            "BGE-Dense": {
                depth: round(data["macro_expected_table_candidate_recall"], 4)
                for depth, data in suite["single_system_coverage"]["BGE-Dense"].items()
            },
            "three_source_union": {
                depth: round(data["macro_expected_table_candidate_recall"], 4)
                for depth, data in suite["union_coverage"]
                ["BGE-Dense + MiniLM Graph + MiniLM Hybrid"].items()
            },
        }
        for suite_name, suite in suites.items()
    }, indent=2))


if __name__ == "__main__":
    main()
