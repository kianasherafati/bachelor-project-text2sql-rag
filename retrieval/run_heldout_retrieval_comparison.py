"""Evaluate the three frozen retrievers on the frozen held-out benchmark."""

from collections import defaultdict

from erp_retrieval_heldout_benchmark import tests
from graph_expanded_retriever import GraphExpandedSchemaRetriever


TOP_K = 10
MODES = ("dense", "hybrid", "graph-expanded")


def evaluate_mode(test, mode, results):
    expected = test["expected_tables"]
    retrieved = [result["full_name"] for result in results]
    missing = [name for name in expected if name not in set(retrieved)]
    return {
        "id": test["id"],
        "difficulty": test["difficulty"],
        "domain": test["domain"],
        "expected": expected,
        "results": results,
        "retrieved": retrieved,
        "missing": missing,
        "recall": (len(expected) - len(missing)) / len(expected),
        "mode": mode,
    }


def validate_benchmark(retriever):
    assert TOP_K == 10
    assert len(tests) == 20
    assert len({test["id"] for test in tests}) == 20
    difficulties = defaultdict(int)
    for test in tests:
        difficulties[test["difficulty"]] += 1
    assert dict(difficulties) == {"easy": 5, "medium": 7, "hard": 8}
    indexed = {document["full_name"] for document in retriever.documents}
    missing = {
        name
        for test in tests
        for name in test["expected_tables"]
        if name not in indexed
    }
    assert not missing, f"Expected tables absent from indexed corpus: {sorted(missing)}"


def score_text(mode, result):
    if mode == "dense":
        return f"score={result['score']:.4f}"
    if mode == "hybrid":
        return (
            f"dense={result['dense_score']:.4f} lexical={result['lexical_score']:.4f} "
            f"combined={result['combined_score']:.4f}"
        )
    return (
        f"hybrid={result['hybrid_score']:.4f} graph={result['graph_signal']:.4f} "
        f"fk_bonus={result['fk_bonus_contribution']:.4f} final={result['final_score']:.4f}"
    )


def print_question_result(item):
    print("-" * 110)
    print(
        f"{item['id']} | mode={item['mode']} | difficulty={item['difficulty']} "
        f"| domain={item['domain']}"
    )
    print("Expected fully qualified tables:")
    for name in item["expected"]:
        print(f"- {name}")
    print(f"Retrieved Top {TOP_K}:")
    for rank, result in enumerate(item["results"], start=1):
        print(f"{rank:2}. {result['full_name']} {score_text(item['mode'], result)}")
    print(f"Recall@{TOP_K}: {item['recall']:.4f}")
    print("Missing expected tables:")
    if item["missing"]:
        for name in item["missing"]:
            print(f"- {name}")
    else:
        print("- None")


def aggregate(items, field=None):
    grouped = defaultdict(list)
    for item in items:
        grouped[item[field] if field else "overall"].append(item)
    return {
        key: {
            "count": len(group),
            "macro_recall": sum(item["recall"] for item in group) / len(group),
            "perfect": sum(item["recall"] == 1.0 for item in group),
        }
        for key, group in grouped.items()
    }


def print_aggregate(mode, items):
    overall = aggregate(items)["overall"]
    print("=" * 110)
    print(f"AGGREGATE | {mode}")
    print(f"Macro-average Recall@{TOP_K}: {overall['macro_recall']:.4f}")
    print(f"Perfect questions: {overall['perfect']}/20")
    print("By difficulty:")
    by_difficulty = aggregate(items, "difficulty")
    for difficulty in ("easy", "medium", "hard"):
        row = by_difficulty[difficulty]
        print(
            f"- {difficulty}: macro Recall@{TOP_K}={row['macro_recall']:.4f}, "
            f"perfect={row['perfect']}/{row['count']}"
        )
    print("By ERP domain:")
    for domain, row in sorted(aggregate(items, "domain").items()):
        print(
            f"- {domain}: macro Recall@{TOP_K}={row['macro_recall']:.4f}, "
            f"perfect={row['perfect']}/{row['count']}"
        )


def result_for_table(item, name):
    return next((result for result in item["results"] if result["full_name"] == name), None)


def print_transitions(label, before, after):
    before_by_id = {item["id"]: item for item in before}
    after_by_id = {item["id"]: item for item in after}
    groups = {"improved": [], "unchanged": [], "regressed": []}
    for test in tests:
        before_item = before_by_id[test["id"]]
        after_item = after_by_id[test["id"]]
        if after_item["recall"] > before_item["recall"]:
            groups["improved"].append(test["id"])
        elif after_item["recall"] < before_item["recall"]:
            groups["regressed"].append(test["id"])
        else:
            groups["unchanged"].append(test["id"])

    print("=" * 110)
    print(f"TRANSITION | {label}")
    for key in ("improved", "unchanged", "regressed"):
        print(f"{key.title()}: {', '.join(groups[key]) or 'None'}")

    for test_id in groups["regressed"]:
        old = before_by_id[test_id]
        new = after_by_id[test_id]
        disappeared = [
            name for name in old["expected"]
            if name in old["retrieved"] and name not in new["retrieved"]
        ]
        entrants = [name for name in new["retrieved"] if name not in old["retrieved"]]
        print(f"Regression details for {test_id}:")
        for name in disappeared:
            old_result = result_for_table(old, name)
            print(f"- Correct table disappeared: {name}; prior {score_text(old['mode'], old_result)}")
        if entrants:
            for name in entrants:
                new_result = result_for_table(new, name)
                print(f"  New entrant: {name}; {score_text(new['mode'], new_result)}")
        else:
            print("  Displacing table: not determinable from the two Top-10 result sets")


def run_benchmark():
    retriever = GraphExpandedSchemaRetriever()
    validate_benchmark(retriever)
    evaluations = {mode: [] for mode in MODES}

    for test in tests:
        dense = retriever.retrieve(test["question"], top_k=TOP_K)
        hybrid = retriever.retrieve_hybrid(test["question"], top_k=TOP_K)
        graph_run = retriever.retrieve_graph_expanded(test["question"], top_k=TOP_K)
        mode_results = {
            "dense": dense,
            "hybrid": hybrid,
            "graph-expanded": graph_run["results"],
        }
        for mode, results in mode_results.items():
            assert len(results) == TOP_K, (
                f"{test['id']} {mode} returned {len(results)} results; expected {TOP_K}"
            )
            item = evaluate_mode(test, mode, results)
            evaluations[mode].append(item)
            print_question_result(item)

    for mode in MODES:
        print_aggregate(mode, evaluations[mode])
    print_transitions("Dense -> Hybrid", evaluations["dense"], evaluations["hybrid"])
    print_transitions(
        "Hybrid -> Graph-expanded",
        evaluations["hybrid"],
        evaluations["graph-expanded"],
    )

    print("=" * 110)
    print("VALIDATION")
    print("Questions: 20")
    print("Difficulty counts: easy=5, medium=7, hard=8")
    print("All expected tables belong to the indexed corpus: True")
    print("All modes returned exactly Top 10 for every question: True")


if __name__ == "__main__":
    run_benchmark()
