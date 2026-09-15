from erp_retrieval_benchmark import tests
from hybrid_retriever import DENSE_WEIGHT, LEXICAL_WEIGHT, HybridSchemaRetriever


TOP_K = 10
BASELINE_AVERAGE_RECALL = 0.4259
BASELINE_PERFECT_TESTS = 2


def run_benchmark():
    retriever = HybridSchemaRetriever()
    test_results = []

    print(
        "Fixed hybrid weights: "
        f"dense={DENSE_WEIGHT:.2f}, lexical={LEXICAL_WEIGHT:.2f}"
    )

    for test_number, test in enumerate(tests, start=1):
        expected_tables = test["expected_tables"]
        retrieval_results = retriever.retrieve_hybrid(
            test["question"],
            top_k=TOP_K,
        )
        retrieved_names = {result["full_name"] for result in retrieval_results}
        missed_tables = [
            name for name in expected_tables if name not in retrieved_names
        ]
        recall = (len(expected_tables) - len(missed_tables)) / len(expected_tables)
        test_results.append({
            "test_number": test_number,
            "recall": recall,
            "missed_tables": missed_tables,
        })

        print("=" * 100)
        print(f"TEST {test_number}")
        print(f"Question: {test['question']}")
        print("Expected tables:")
        for name in expected_tables:
            print(f"- {name}")
        print(f"Top {TOP_K} hybrid results:")
        for rank, result in enumerate(retrieval_results, start=1):
            print(
                f"{rank:2}. {result['full_name']} "
                f"dense={result['dense_score']:.4f} "
                f"lexical={result['lexical_score']:.4f} "
                f"combined={result['combined_score']:.4f}"
            )
        print(f"Recall@{TOP_K}: {recall:.4f}")
        print("Missed expected tables:")
        if missed_tables:
            for name in missed_tables:
                print(f"- {name}")
        else:
            print("- None")

    average_recall = sum(item["recall"] for item in test_results) / len(test_results)
    perfect_tests = [
        item["test_number"] for item in test_results if item["recall"] == 1.0
    ]
    missing_tests = [
        item["test_number"] for item in test_results if item["missed_tables"]
    ]

    print("\n" + "=" * 100)
    print("HYBRID BENCHMARK SUMMARY")
    for item in test_results:
        print(f"- Test {item['test_number']}: Recall@{TOP_K}={item['recall']:.4f}")
    print(f"Hybrid Average Recall@{TOP_K}: {average_recall:.4f}")
    print(f"Perfect tests: {len(perfect_tests)}/9 ({perfect_tests})")
    print(f"Tests missing at least one expected table: {missing_tests}")
    print(
        "Dense baseline comparison: "
        f"Average Recall@{TOP_K}={BASELINE_AVERAGE_RECALL:.4f}, "
        f"Perfect={BASELINE_PERFECT_TESTS}/9"
    )
    print(f"Test 1 remains perfect: {1 in perfect_tests}")
    print(f"Test 6 remains perfect: {6 in perfect_tests}")
    success = (
        average_recall >= 0.65
        and len(perfect_tests) >= 5
        and 1 in perfect_tests
        and 6 in perfect_tests
    )
    print(f"Pre-defined success criteria met: {success}")


if __name__ == "__main__":
    run_benchmark()
