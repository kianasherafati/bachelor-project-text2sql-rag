from erp_retrieval_benchmark import tests
from retriever import SchemaRetriever


TOP_K = 10


def run_benchmark():
    retriever = SchemaRetriever()
    test_results = []

    for test_number, test in enumerate(tests, start=1):
        question = test["question"]
        expected_tables = test["expected_tables"]

        retrieval_results = retriever.retrieve(
            question,
            top_k=TOP_K
        )

        retrieved_table_names = {
            result["full_name"]
            for result in retrieval_results
        }
        found_expected_tables = [
            table_name
            for table_name in expected_tables
            if table_name in retrieved_table_names
        ]
        missed_expected_tables = [
            table_name
            for table_name in expected_tables
            if table_name not in retrieved_table_names
        ]
        recall = (
            len(found_expected_tables)
            / len(expected_tables)
        )

        test_results.append({
            "test_number": test_number,
            "recall": recall,
        })

        print("=" * 80)
        print(f"TEST {test_number}")
        print("Question:")
        print(question)

        print("\nExpected tables:")
        for table_name in expected_tables:
            print(f"- {table_name}")

        print(f"\nTop {TOP_K} retrieved tables:")
        for rank, result in enumerate(
            retrieval_results,
            start=1
        ):
            print(
                f"{rank:2}. {result['full_name']} "
                f"(score={result['score']:.4f})"
            )

        print("\nFound expected tables:")
        if found_expected_tables:
            for table_name in found_expected_tables:
                print(f"- {table_name}")
        else:
            print("- None")

        print("\nMissed expected tables:")
        if missed_expected_tables:
            for table_name in missed_expected_tables:
                print(f"- {table_name}")
        else:
            print("- None")

        print(f"\nRecall@{TOP_K}: {recall:.4f}")

    average_recall = (
        sum(result["recall"] for result in test_results)
        / len(test_results)
        if test_results
        else 0.0
    )
    perfect_recall_count = sum(
        result["recall"] == 1.0
        for result in test_results
    )
    missed_test_count = sum(
        result["recall"] < 1.0
        for result in test_results
    )

    print("\n" + "=" * 80)
    print("BENCHMARK SUMMARY")
    print(f"Recall@{TOP_K} by test:")
    for result in test_results:
        print(
            f"- Test {result['test_number']}: "
            f"{result['recall']:.4f}"
        )

    print(f"Average Recall@{TOP_K}: {average_recall:.4f}")
    print(
        f"Tests with perfect Recall@{TOP_K}: "
        f"{perfect_recall_count}"
    )
    print(
        "Tests missing at least one expected table: "
        f"{missed_test_count}"
    )


if __name__ == "__main__":
    run_benchmark()
