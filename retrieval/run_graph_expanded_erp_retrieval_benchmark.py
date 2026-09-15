from erp_retrieval_benchmark import tests
from graph_expanded_retriever import (
    FIXED_FK_BONUS,
    GraphExpandedSchemaRetriever,
)


TOP_K = 10


def run_benchmark():
    retriever = GraphExpandedSchemaRetriever()
    test_results = []
    regressions = []

    print(
        "Fixed graph policy: graph_signal = seed_hybrid_score / "
        "log2(seed_rank + 1)"
    )
    print(f"Fixed FK bonus: {FIXED_FK_BONUS:.2f}")
    print("Final score = hybrid_score + fixed_fk_bonus * graph_signal")

    for test_number, test in enumerate(tests, start=1):
        run = retriever.retrieve_graph_expanded(test["question"], top_k=TOP_K)
        seeds = run["original_hybrid_top_10"]
        final_results = run["results"]
        expected = test["expected_tables"]
        seed_names = {result["full_name"] for result in seeds}
        final_names = {result["full_name"] for result in final_results}
        missing = [name for name in expected if name not in final_names]
        recall = (len(expected) - len(missing)) / len(expected)

        for name in expected:
            if name in seed_names and name not in final_names:
                displaced = next(result for result in seeds if result["full_name"] == name)
                entrants = [
                    result for result in final_results
                    if result["full_name"] not in seed_names
                ]
                displacer = min(
                    entrants,
                    key=lambda result: result["final_score"],
                ) if entrants else None
                regressions.append({
                    "test_number": test_number,
                    "displaced": displaced,
                    "displacer": displacer,
                })

        test_results.append({
            "test_number": test_number,
            "recall": recall,
            "missing": missing,
        })

        print("=" * 110)
        print(f"TEST {test_number}")
        print(f"Question: {test['question']}")
        print("Expected tables:")
        for name in expected:
            print(f"- {name}")
        print("Original Hybrid Top 10:")
        for rank, result in enumerate(seeds, start=1):
            print(f"{rank:2}. {result['full_name']} hybrid={result['combined_score']:.4f}")
        print(f"Expanded candidate pool size: {run['expanded_candidate_pool_size']}")
        print("Final graph-aware Top 10:")
        for rank, result in enumerate(final_results, start=1):
            sources = ", ".join(result["source_seed_tables"]) or "None"
            print(
                f"{rank:2}. {result['full_name']} "
                f"hybrid={result['hybrid_score']:.4f} "
                f"graph={result['graph_signal']:.4f} "
                f"fk_bonus={result['fk_bonus_contribution']:.4f} "
                f"final={result['final_score']:.4f} "
                f"hybrid_seed={result['is_hybrid_seed']} "
                f"sources=[{sources}]"
            )
        print(f"Recall@{TOP_K}: {recall:.4f}")
        print("Missing expected tables:")
        if missing:
            for name in missing:
                print(f"- {name}")
        else:
            print("- None")

    average_recall = sum(result["recall"] for result in test_results) / len(test_results)
    perfect = [result["test_number"] for result in test_results if result["recall"] == 1.0]
    missing_tests = [result["test_number"] for result in test_results if result["missing"]]

    print("\n" + "=" * 110)
    print("GRAPH-EXPANDED BENCHMARK SUMMARY")
    print("Dense baseline: Average Recall@10=0.4259, Perfect=2/9")
    print("Hybrid baseline: Average Recall@10=0.6296, Perfect=3/9")
    print(f"Graph-expanded Average Recall@10: {average_recall:.4f}")
    print(f"Perfect tests: {len(perfect)}/9 ({perfect})")
    print(f"Tests missing at least one expected table: {missing_tests}")
    print(f"Tests 1, 2, and 9 remain perfect: {all(n in perfect for n in (1, 2, 9))}")
    success = (
        average_recall >= 0.85
        and len(perfect) >= 6
        and all(number in perfect for number in (1, 2, 9))
    )
    print(f"Pre-defined success criteria met: {success}")

    print("Regression analysis:")
    if not regressions:
        print("- No previously correct Hybrid Top-10 expected table was displaced.")
    for regression in regressions:
        displaced = regression["displaced"]
        displacer = regression["displacer"]
        print(
            f"- Test {regression['test_number']}: {displaced['full_name']} "
            f"was displaced (hybrid={displaced['combined_score']:.4f})."
        )
        if displacer:
            print(
                f"  Displacer: {displacer['full_name']} "
                f"hybrid={displacer['hybrid_score']:.4f}, "
                f"graph={displacer['graph_signal']:.4f}, "
                f"fk_bonus={displacer['fk_bonus_contribution']:.4f}, "
                f"final={displacer['final_score']:.4f}; "
                f"caused_by_fk_boost={displacer['fk_bonus_contribution'] > 0.0}."
            )


if __name__ == "__main__":
    run_benchmark()
