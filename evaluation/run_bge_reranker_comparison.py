"""Run the single frozen BGE reranker evaluation after all preflights pass."""

from __future__ import annotations

from collections import defaultdict
import hashlib
import json
import math
from pathlib import Path
import re
import statistics
import sys
import time

import psutil


ROOT = Path(__file__).resolve().parents[1]
RETRIEVAL = ROOT / "retrieval"
sys.path.insert(0, str(RETRIEVAL))

from bge_reranker_v2_m3 import FrozenBGEReranker, REVISION  # noqa: E402


CANDIDATES_PATH = ROOT / "evaluation" / "bge_reranker_candidate_lists.json"
REPRESENTATIONS_PATH = RETRIEVAL / "bge_reranker_table_representations.json"
AUDIT_PATH = RETRIEVAL / "bge_reranker_representation_audit.json"
PREFLIGHT_PATH = ROOT / "evaluation" / "bge_reranker_pair_preflight.json"
BASELINE_PATH = ROOT / "evaluation" / "bge_m3_retrieval_comparison_results.json"
JOURNAL_PATH = ROOT / "evaluation" / "bge_reranker_scoring_journal.jsonl"
OUTPUT_PATH = ROOT / "evaluation" / "bge_reranker_comparison_results.json"
SUITE_ORDER = ["development_9", "heldout_schema_20", "real_world_observed_13"]
STOPWORDS = {
    "a", "an", "and", "as", "at", "be", "by", "each", "for", "from", "in",
    "including", "into", "is", "it", "of", "on", "only", "or", "show", "the",
    "their", "to", "with",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def verify_frozen_hashes(preflight: dict) -> None:
    for relative, expected in preflight["frozen_artifact_sha256"].items():
        path = ROOT / relative
        if not path.is_file() or sha256_file(path) != expected:
            raise RuntimeError(f"Frozen artifact changed after preflight: {relative}")


def percentile(values, fraction):
    ordered = sorted(values)
    return ordered[max(0, math.ceil(fraction * len(ordered)) - 1)]


def words(text):
    expanded = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", text)
    return {
        token.casefold()
        for token in re.findall(r"[A-Za-z][A-Za-z0-9]*", expanded)
        if len(token) > 2 and token.casefold() not in STOPWORDS
    }


def evidence_diagnostic(question, table_audit):
    query_terms = words(question)
    included = []
    omitted = []
    for key, destination in (("included_columns", included), ("omitted_columns", omitted)):
        for column in table_audit[key]:
            evidence = [column["physical_column_name"], *column["included_captions"]]
            evidence_terms = set().union(*(words(value) for value in evidence)) if evidence else set()
            matches = sorted(query_terms.intersection(evidence_terms))
            if matches:
                destination.append({
                    "column": column["physical_column_name"],
                    "matched_question_terms": matches,
                    "english_captions": column["included_captions"],
                })
    return {
        "included_column_evidence_matches": included,
        "omitted_column_evidence_matches": omitted,
        "relevant_evidence_omitted": bool(omitted),
        "diagnostic_method": "case-insensitive English token overlap; diagnostic only, not used for scoring",
    }


def aggregate(rows):
    recalls = [row["recall_at_10"] for row in rows]
    by_difficulty = defaultdict(list)
    by_domain = defaultdict(list)
    for row in rows:
        by_difficulty[str(row["difficulty"])].append(row["recall_at_10"])
        by_domain[str(row["domain"])].append(row["recall_at_10"])
    summarize = lambda values: {
        "question_count": len(values),
        "macro_recall_at_10": statistics.mean(values),
    }
    return {
        "question_count": len(rows),
        "macro_recall_at_10": statistics.mean(recalls),
        "full_coverage_count": sum(row["full_coverage"] for row in rows),
        "by_difficulty": {key: summarize(value) for key, value in sorted(by_difficulty.items())},
        "by_domain": {key: summarize(value) for key, value in sorted(by_domain.items())},
    }


def transitions(reranker_rows, baseline_rows):
    baseline_by_id = {row["id"]: row for row in baseline_rows}
    groups = {"improved": [], "unchanged": [], "regressed": []}
    for row in reranker_rows:
        old = baseline_by_id[row["id"]]["recall_at_10"]
        new = row["recall_at_10"]
        label = "improved" if new > old else "regressed" if new < old else "unchanged"
        groups[label].append({"id": row["id"], "baseline": old, "reranker": new, "delta": new - old})
    return groups


def read_journal():
    if not JOURNAL_PATH.is_file():
        return None, {}
    entries = [json.loads(line) for line in JOURNAL_PATH.read_text(encoding="utf-8").splitlines() if line.strip()]
    if not entries or entries[0].get("kind") != "warmup":
        raise RuntimeError("Existing scoring journal lacks its single warm-up record")
    scores = {}
    for entry in entries[1:]:
        if entry.get("kind") != "benchmark_pair":
            raise RuntimeError("Unexpected scoring-journal entry")
        key = (entry["suite"], entry["case_id"], entry["table"])
        if key in scores:
            raise RuntimeError(f"Duplicate score in journal: {key}")
        scores[key] = entry
    return entries[0], scores


def append_journal(entry):
    with JOURNAL_PATH.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(entry, ensure_ascii=False, separators=(",", ":")) + "\n")
        handle.flush()


def main():
    if OUTPUT_PATH.exists():
        raise RuntimeError("Frozen evaluation output already exists; refusing to score again")
    preflight = json.loads(PREFLIGHT_PATH.read_text(encoding="utf-8"))
    if preflight["status"] != "passed" or preflight["unique_candidate_pairs"] != 2931:
        raise RuntimeError("Pair preflight has not passed")
    verify_frozen_hashes(preflight)
    candidates = json.loads(CANDIDATES_PATH.read_text(encoding="utf-8"))
    representations_payload = json.loads(REPRESENTATIONS_PATH.read_text(encoding="utf-8"))
    audit_payload = json.loads(AUDIT_PATH.read_text(encoding="utf-8"))
    baseline = json.loads(BASELINE_PATH.read_text(encoding="utf-8"))
    representation_by_table = {
        item["fully_qualified_table"]: item for item in representations_payload["tables"]
    }
    audit_by_table = {item["fully_qualified_table"]: item for item in audit_payload["tables"]}
    if len(representation_by_table) != 2196 or len(audit_by_table) != 2196:
        raise RuntimeError("Representation corpus changed")

    process = psutil.Process()
    run_started = time.perf_counter()
    reranker = FrozenBGEReranker()
    peak_rss = max(process.memory_info().rss, reranker.peak_observed_rss_bytes)
    warmup, scored = read_journal()
    if warmup is None:
        warm_question = "Which demonstration table contains a maintenance schedule?"
        warm_document = "Identity: fully-qualified table demo.tblMaintenance; physical table tblMaintenance; schema demo\nColumns: ID; ScheduleDate; Notes"
        score, latency, pair_tokens = reranker.score(warm_question, warm_document)
        warmup = {
            "kind": "warmup",
            "pair_kind": "nonbenchmark",
            "model_revision": REVISION,
            "raw_logit": score,
            "latency_seconds": latency,
            "encoded_pair_tokens": pair_tokens,
            "finite_scalar_logit": math.isfinite(score),
        }
        append_journal(warmup)
        print(json.dumps({"event": "single_fresh_warmup_complete", **warmup}), flush=True)

    expected_keys = []
    for suite_name in SUITE_ORDER:
        for case in candidates["suites"][suite_name]["cases"]:
            for candidate in case["union_candidates"]:
                expected_keys.append((suite_name, case["id"], candidate["table"]))
    if len(expected_keys) != 2931 or len(set(expected_keys)) != 2931:
        raise RuntimeError("Candidate pairs changed")
    unknown_journal_keys = set(scored).difference(expected_keys)
    if unknown_journal_keys:
        raise RuntimeError("Scoring journal contains pairs outside the frozen candidate artifact")

    benchmark_started = time.perf_counter()
    newly_scored = 0
    for ordinal, key in enumerate(expected_keys, start=1):
        if key in scored:
            continue
        suite_name, case_id, table = key
        case = next(item for item in candidates["suites"][suite_name]["cases"] if item["id"] == case_id)
        representation = representation_by_table[table]
        score, latency, pair_tokens = reranker.score(case["question"], representation["text"])
        entry = {
            "kind": "benchmark_pair",
            "suite": suite_name,
            "case_id": case_id,
            "table": table,
            "raw_logit": score,
            "latency_seconds": latency,
            "pair_tokens": pair_tokens,
        }
        append_journal(entry)
        scored[key] = entry
        newly_scored += 1
        peak_rss = max(peak_rss, process.memory_info().rss, reranker.peak_observed_rss_bytes)
        if ordinal % 25 == 0 or ordinal == len(expected_keys):
            print(json.dumps({
                "event": "progress",
                "completed_pairs": len(scored),
                "total_pairs": len(expected_keys),
                "latest_ordinal": ordinal,
            }), flush=True)
    benchmark_wall_seconds = time.perf_counter() - benchmark_started
    if len(scored) != 2931:
        raise RuntimeError("Scoring did not produce exactly 2,931 results")

    output_suites = {}
    all_pair_latencies = []
    question_latencies = []
    failure_counts = defaultdict(int)
    for suite_name in SUITE_ORDER:
        rows = []
        for case in candidates["suites"][suite_name]["cases"]:
            candidate_by_table = {item["table"]: item for item in case["union_candidates"]}
            ranked = sorted(
                (
                    {
                        "table": table,
                        "reranker_raw_logit": scored[(suite_name, case["id"], table)]["raw_logit"],
                        "pair_tokens": scored[(suite_name, case["id"], table)]["pair_tokens"],
                        "latency_seconds": scored[(suite_name, case["id"], table)]["latency_seconds"],
                        "candidate_sources": candidate_by_table[table]["sources"],
                        "bge_dense_source": candidate_by_table[table]["bge_dense"],
                        "minilm_graph_source": candidate_by_table[table]["minilm_graph"],
                    }
                    for table in candidate_by_table
                ),
                key=lambda item: (-item["reranker_raw_logit"], item["table"]),
            )
            for rank, item in enumerate(ranked, start=1):
                item["rank"] = rank
                all_pair_latencies.append(item["latency_seconds"])
            question_latency = sum(item["latency_seconds"] for item in ranked)
            question_latencies.append(question_latency)
            top10 = ranked[:10]
            top_names = {item["table"] for item in top10}
            candidate_names = set(candidate_by_table)
            expected = case["expected_tables"]
            candidate_expected = [table for table in expected if table in candidate_names]
            missing = [table for table in expected if table not in top_names]
            failures = []
            for table in missing:
                if table not in candidate_names:
                    failure_type = "A_candidate_generation_failure"
                    rank = None
                else:
                    failure_type = "B_reranker_failure"
                    rank = next(item["rank"] for item in ranked if item["table"] == table)
                failure_counts[failure_type] += 1
                failures.append({
                    "table": table,
                    "classification": failure_type,
                    "reranker_rank": rank,
                    "representation_evidence": evidence_diagnostic(case["question"], audit_by_table[table]),
                })
            capacity_limited = len(candidate_expected) > 10
            if capacity_limited:
                failure_counts["C_capacity_limited_cases"] += 1
            labels = {
                table: {
                    "included_table_labels": audit_by_table[table]["included_table_labels"],
                    "included_form_labels": audit_by_table[table]["included_form_labels"],
                    "included_module_labels": audit_by_table[table]["included_module_labels"],
                    "omitted_table_labels": audit_by_table[table]["omitted_table_labels"],
                    "omitted_form_labels": audit_by_table[table]["omitted_form_labels"],
                    "omitted_module_labels": audit_by_table[table]["omitted_module_labels"],
                }
                for table in expected
            }
            rows.append({
                "id": case["id"],
                "question": case["question"],
                "difficulty": case["difficulty"],
                "domain": case["domain"],
                "expected_tables": expected,
                "candidate_count": len(ranked),
                "candidate_expected_tables": candidate_expected,
                "candidate_recall": len(candidate_expected) / len(expected),
                "capacity_adjusted_oracle_recall_at_10": min(10, len(candidate_expected)) / len(expected),
                "retrieved_top_10": top10,
                "missing_expected_tables": missing,
                "recall_at_10": (len(expected) - len(missing)) / len(expected),
                "full_coverage": not missing,
                "capacity_limitation": capacity_limited,
                "miss_failures": failures,
                "expected_table_business_metadata": labels,
                "candidate_set_scoring_seconds": question_latency,
            })
        output_suites[suite_name] = {
            "cases": rows,
            "aggregate": aggregate(rows),
            "candidate_macro_recall": statistics.mean(row["candidate_recall"] for row in rows),
            "capacity_adjusted_oracle_macro_recall_at_10": statistics.mean(
                row["capacity_adjusted_oracle_recall_at_10"] for row in rows
            ),
            "oracle_to_reranker_gap": statistics.mean(
                row["capacity_adjusted_oracle_recall_at_10"] - row["recall_at_10"] for row in rows
            ),
            "comparisons": {
                system: transitions(rows, baseline["suites"][suite_name]["per_system"][system])
                for system in ("MiniLM Graph", "BGE-Dense", "BGE-Graph")
            },
            "baseline_aggregates": {
                system: baseline["suites"][suite_name]["aggregates"][system]
                for system in ("MiniLM Graph", "BGE-Dense", "BGE-Graph")
            },
        }

    real_c04 = next(
        row for row in output_suites["real_world_observed_13"]["cases"] if row["id"] == "REAL-C04"
    )
    verify_frozen_hashes(preflight)
    integrity = {
        "frozen_hashes_unchanged_before_and_after": True,
        "candidate_source_depths": {"bge_dense": 50, "minilm_graph": 50},
        "unique_candidate_pairs": len(scored),
        "table_representations": len(representation_by_table),
        "identity_budget": 68,
        "columns_budget": 536,
        "document_budget": 892,
        "question_budget": 128,
        "pair_max": 1024,
        "maximum_actual_pair_tokens": preflight["actual_tokens"]["maximum_pair"],
        "silent_truncation": False,
        "model_revision": REVISION,
        "precision": "float32",
        "device": "cpu",
        "batch_size": 1,
        "reranker_score_only": True,
        "score_fusion": False,
        "post_reranker_graph_expansion": False,
        "database_accessed": False,
        "sql_executed": False,
        "qwen_run": False,
        "tickets_accessed": False,
        "unseen_benchmark_inspected": False,
        "post_result_tuning": False,
        "newly_scored_pairs_this_invocation": newly_scored,
    }
    result = {
        "experiment": "frozen_bge_reranker_v2_m3_candidate_union_revision_68_536",
        "warmup": warmup,
        "representation_preflight": json.loads((RETRIEVAL / "bge_reranker_identity_preflight.json").read_text(encoding="utf-8")),
        "representation_build_report": json.loads((RETRIEVAL / "bge_reranker_representation_build_report.json").read_text(encoding="utf-8")),
        "pair_preflight": preflight,
        "candidate_artifact_verification": {
            "sha256": sha256_file(CANDIDATES_PATH),
            "combined_candidate_count": candidates["combined_candidate_count"],
            "coverage": {name: candidates["suites"][name]["coverage"] for name in SUITE_ORDER},
        },
        "performance": {
            "model_load_seconds": reranker.model_load_seconds,
            "fresh_nonbenchmark_warmup_seconds": warmup["latency_seconds"],
            "benchmark_scoring_wall_seconds_this_invocation": benchmark_wall_seconds,
            "total_run_wall_seconds": time.perf_counter() - run_started,
            "pair_latency_seconds": {
                "mean": statistics.mean(all_pair_latencies),
                "median": statistics.median(all_pair_latencies),
                "p95": percentile(all_pair_latencies, 0.95),
                "maximum": max(all_pair_latencies),
            },
            "question_candidate_set_latency_seconds": {
                "mean": statistics.mean(question_latencies),
                "median": statistics.median(question_latencies),
                "p95": percentile(question_latencies, 0.95),
                "maximum": max(question_latencies),
            },
            "peak_process_rss_bytes": peak_rss,
            "representation_build_seconds": json.loads((RETRIEVAL / "bge_reranker_representation_build_report.json").read_text(encoding="utf-8"))["build_seconds"],
        },
        "suites": output_suites,
        "failure_counts": dict(sorted(failure_counts.items())),
        "real_c04": {
            "expected_table_count": len(real_c04["expected_tables"]),
            "expected_tables_in_candidate_pool": len(real_c04["candidate_expected_tables"]),
            "candidate_recall": real_c04["candidate_recall"],
            "attainable_recall_at_10": real_c04["capacity_adjusted_oracle_recall_at_10"],
            "actual_recall_at_10": real_c04["recall_at_10"],
            "missing_expected_tables": real_c04["missing_expected_tables"],
            "candidate_generation_failures": [
                item["table"] for item in real_c04["miss_failures"]
                if item["classification"] == "A_candidate_generation_failure"
            ],
            "capacity_limitation": real_c04["capacity_limitation"],
        },
        "integrity": integrity,
    }
    OUTPUT_PATH.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "event": "frozen_evaluation_complete",
        "output": str(OUTPUT_PATH),
        "suite_results": {
            name: {
                "candidate_macro_recall": data["candidate_macro_recall"],
                "oracle_macro_recall_at_10": data["capacity_adjusted_oracle_macro_recall_at_10"],
                "reranker_macro_recall_at_10": data["aggregate"]["macro_recall_at_10"],
                "full_coverage_count": data["aggregate"]["full_coverage_count"],
            }
            for name, data in output_suites.items()
        },
        "failure_counts": result["failure_counts"],
        "performance": result["performance"],
    }, indent=2), flush=True)


if __name__ == "__main__":
    main()
