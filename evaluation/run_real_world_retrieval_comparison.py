"""Evaluate the three frozen retrievers on the frozen real-world benchmark."""

from collections import Counter, defaultdict
import hashlib
import os
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
EVALUATION_DIR = ROOT / "evaluation"
RETRIEVAL_DIR = ROOT / "retrieval"
sys.path.insert(0, str(EVALUATION_DIR))
sys.path.insert(0, str(RETRIEVAL_DIR))

# The frozen model is already cached locally. Prevent the model loader from
# making an unrelated metadata request during this artifact-only evaluation.
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")

from real_world_text2sql_benchmark import tests
from graph_expanded_retriever import GraphExpandedSchemaRetriever


TOP_K = 10
MODES = ("dense", "hybrid", "graph-expanded")
C04_ID = "REAL-C04"


def protected_paths():
    """Files whose immutability matters for this frozen evaluation."""
    paths = [ROOT / "evaluation" / "real_world_text2sql_benchmark.py"]
    for path in RETRIEVAL_DIR.rglob("*"):
        if (
            path.is_file()
            and "__pycache__" not in path.parts
            and path.suffix.lower()
            in {".py", ".json", ".index", ".pkl", ".npy", ".faiss", ".bin", ".pt", ".safetensors"}
        ):
            paths.append(path)
    return sorted(set(paths))


def hashes(paths):
    return {
        str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in paths
    }


def validate_benchmark(retriever):
    assert TOP_K == 10
    assert len(tests) == 13
    assert len({test["id"] for test in tests}) == 13
    assert Counter(test["difficulty"] for test in tests) == {
        "easy": 4,
        "medium": 5,
        "hard": 4,
    }
    c04 = next(test for test in tests if test["id"] == C04_ID)
    assert c04["expected_table_count"] == 12
    assert c04["top10_full_coverage_possible"] is False
    assert abs(c04["top10_recall_ceiling"] - 10 / 12) < 1e-12
    assert sum(test["top10_full_coverage_possible"] for test in tests) == 12
    indexed = {document["full_name"] for document in retriever.documents}
    missing = {
        table
        for test in tests
        for table in test["expected_tables"]
        if table not in indexed
    }
    assert not missing, f"Expected tables absent from indexed corpus: {sorted(missing)}"


def evaluate_mode(test, mode, results):
    expected = test["expected_tables"]
    retrieved = [result["full_name"] for result in results]
    retrieved_set = set(retrieved)
    missing = [table for table in expected if table not in retrieved_set]
    hit_count = len(expected) - len(missing)
    ceiling_hits = min(TOP_K, len(expected))
    return {
        "id": test["id"],
        "question": test["question"],
        "difficulty": test["difficulty"],
        "domain": test["domain"],
        "expected": expected,
        "results": results,
        "retrieved": retrieved,
        "missing": missing,
        "hit_count": hit_count,
        "recall": hit_count / len(expected),
        "reached_top10_ceiling": hit_count == ceiling_hits,
        "mode": mode,
    }


def score_text(mode, result):
    if mode == "dense":
        return f"score={result['score']:.6f}"
    if mode == "hybrid":
        return (
            f"dense={result['dense_score']:.6f} "
            f"lexical={result['lexical_score']:.6f} "
            f"combined={result['combined_score']:.6f}"
        )
    sources = ",".join(result["source_seed_tables"]) or "None"
    return (
        f"hybrid={result['hybrid_score']:.6f} "
        f"graph={result['graph_signal']:.6f} "
        f"fk_contribution={result['fk_bonus_contribution']:.6f} "
        f"final={result['final_score']:.6f} "
        f"hybrid_seed={result['is_hybrid_seed']} "
        f"fk_sources={sources}"
    )


def print_case(item):
    print("-" * 120)
    print(
        f"{item['id']} | {item['mode']} | {item['difficulty']} | {item['domain']}"
    )
    print("Question:", item["question"])
    print("Expected:", ", ".join(item["expected"]))
    print(f"Retrieved Top {TOP_K}:")
    for rank, result in enumerate(item["results"], start=1):
        print(
            f"{rank:2}. {result['full_name']} | "
            f"{score_text(item['mode'], result)}"
        )
    print("Missing:", ", ".join(item["missing"]) or "None")
    print(f"Recall@{TOP_K}: {item['recall']:.4f}")
    if item["id"] == C04_ID:
        print(
            "C04 ceiling: "
            f"{item['hit_count']}/12 expected tables; "
            f"10/12 ceiling reached={item['reached_top10_ceiling']}"
        )


def aggregate(items, field=None):
    grouped = defaultdict(list)
    for item in items:
        grouped[item[field] if field else "overall"].append(item)
    return {
        key: {
            "count": len(group),
            "macro_recall": sum(item["recall"] for item in group) / len(group),
            "full_coverage": sum(item["recall"] == 1.0 for item in group),
        }
        for key, group in grouped.items()
    }


def print_aggregate(mode, items):
    overall = aggregate(items)["overall"]
    eligible = [item for item in items if item["id"] != C04_ID]
    eligible_full = sum(item["recall"] == 1.0 for item in eligible)
    print("=" * 120)
    print(f"AGGREGATE | {mode}")
    print(f"Macro-average Recall@{TOP_K}: {overall['macro_recall']:.4f}")
    print(
        f"Full expected-table coverage: {overall['full_coverage']}/13 "
        "(C04 cannot achieve full coverage with Top 10)"
    )
    print(f"Fully covered among Top-10-eligible cases: {eligible_full}/12")
    print("By difficulty:")
    by_difficulty = aggregate(items, "difficulty")
    for difficulty in ("easy", "medium", "hard"):
        row = by_difficulty[difficulty]
        print(
            f"- {difficulty}: count={row['count']} "
            f"macro_recall={row['macro_recall']:.4f} "
            f"full_coverage={row['full_coverage']}/{row['count']}"
        )
    print("By domain:")
    for domain, row in sorted(aggregate(items, "domain").items()):
        print(
            f"- {domain}: count={row['count']} "
            f"macro_recall={row['macro_recall']:.4f} "
            f"full_coverage={row['full_coverage']}/{row['count']}"
        )


def result_for_table(item, table):
    return next(
        (result for result in item["results"] if result["full_name"] == table),
        None,
    )


def print_transitions(label, before, after):
    before_by_id = {item["id"]: item for item in before}
    after_by_id = {item["id"]: item for item in after}
    groups = {"improved": [], "unchanged": [], "regressed": []}
    for test in tests:
        old = before_by_id[test["id"]]
        new = after_by_id[test["id"]]
        if new["recall"] > old["recall"]:
            groups["improved"].append(test["id"])
        elif new["recall"] < old["recall"]:
            groups["regressed"].append(test["id"])
        else:
            groups["unchanged"].append(test["id"])
    print("=" * 120)
    print("TRANSITION |", label)
    for key in ("improved", "unchanged", "regressed"):
        print(f"{key.title()}: {', '.join(groups[key]) or 'None'}")
    for test_id in groups["regressed"]:
        old = before_by_id[test_id]
        new = after_by_id[test_id]
        disappeared = [
            table
            for table in old["expected"]
            if table in old["retrieved"] and table not in new["retrieved"]
        ]
        entrants = [
            table for table in new["retrieved"] if table not in old["retrieved"]
        ]
        print(f"Regression details | {test_id}")
        for table in disappeared:
            result = result_for_table(old, table)
            print(
                f"- Lost expected table: {table}; "
                f"prior {score_text(old['mode'], result)}"
            )
        if entrants:
            for table in entrants:
                result = result_for_table(new, table)
                print(
                    f"- Competing entrant: {table}; "
                    f"{score_text(new['mode'], result)}"
                )
        else:
            print("- Displacing table is not determinable from the two Top-10 sets")


def print_c04(evaluations):
    print("=" * 120)
    print("REAL-C04 ANALYSIS | theoretical Top-10 ceiling=10/12=0.8333")
    for mode in MODES:
        item = next(row for row in evaluations[mode] if row["id"] == C04_ID)
        print(
            f"- {mode}: retrieved={item['hit_count']}/12 "
            f"recall={item['recall']:.4f} "
            f"ceiling_reached={item['reached_top10_ceiling']} "
            f"missed={', '.join(item['missing']) or 'None'}"
        )


def run_benchmark():
    paths = protected_paths()
    before = hashes(paths)
    retriever = GraphExpandedSchemaRetriever()
    validate_benchmark(retriever)
    evaluations = {mode: [] for mode in MODES}
    for test in tests:
        runs = {
            "dense": retriever.retrieve(test["question"], top_k=TOP_K),
            "hybrid": retriever.retrieve_hybrid(test["question"], top_k=TOP_K),
            "graph-expanded": retriever.retrieve_graph_expanded(
                test["question"], top_k=TOP_K
            )["results"],
        }
        for mode, results in runs.items():
            assert len(results) == TOP_K, (
                f"{test['id']} {mode} returned {len(results)}; expected {TOP_K}"
            )
            assert len({result["full_name"] for result in results}) == TOP_K
            item = evaluate_mode(test, mode, results)
            evaluations[mode].append(item)
            print_case(item)
    for mode in MODES:
        print_aggregate(mode, evaluations[mode])
    print_transitions(
        "Dense -> Hybrid", evaluations["dense"], evaluations["hybrid"]
    )
    print_transitions(
        "Hybrid -> Graph-expanded",
        evaluations["hybrid"],
        evaluations["graph-expanded"],
    )
    print_c04(evaluations)
    after = hashes(paths)
    assert before == after, "Frozen benchmark or retrieval artifacts changed"
    print("=" * 120)
    print("VALIDATION")
    print("Cases evaluated: 13")
    print("Difficulty counts: easy=4, medium=5, hard=4")
    print("Every expected table belongs to the indexed corpus: True")
    print("Exactly 10 unique final results per mode and case: True")
    print("Frozen benchmark and retrieval artifacts unchanged: True")
    print("Top_k: 10")
    print("Tuning after results: False")
    return evaluations


if __name__ == "__main__":
    run_benchmark()
