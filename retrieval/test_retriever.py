from retriever import SchemaRetriever


retriever = SchemaRetriever()

test_cases = [
    {
        "question":
            "Show all products ordered by total sales quantity "
            "from highest to lowest.",
        "required_tables": {
            "dbo.Product",
            "dbo.SalesInvoiceItem",
        },
    },
    {
        "question":
            "Show inventory movements for each product.",
        "required_tables": {
            "dbo.InventoryTransaction",
            "dbo.Product",
        },
    },
    {
        "question":
            "Show employees hired after 2025.",
        "required_tables": {
            "dbo.Employee",
        },
    },
    {
        "question":
            "Show customers from Berlin.",
        "required_tables": {
            "dbo.Customer",
        },
    },
    {
        "question":
            "Show each invoice item and its unit price.",
        "required_tables": {
            "dbo.SalesInvoiceItem",
        },
    },
]


for test_number, case in enumerate(
    test_cases,
    start=1
):
    question = case["question"]
    required_tables = case["required_tables"]

    results = retriever.retrieve(
        question,
        top_k=3
    )

    retrieved_tables = {
        result["full_name"]
        for result in results
    }

    relevant_retrieved = (
        retrieved_tables
        & required_tables
    )

    recall = (
        len(relevant_retrieved)
        / len(required_tables)
    )

    precision = (
        len(relevant_retrieved)
        / len(retrieved_tables)
    )

    print("=" * 80)
    print(f"TEST {test_number}")

    print("\nQuestion:")
    print(question)

    print("\nRequired:")
    print(required_tables)

    print("\nRetrieved:")

    for rank, result in enumerate(
        results,
        start=1
    ):
        print(
            rank,
            result["full_name"],
            round(result["score"], 4)
        )

    print(
        "\nRecall@3:",
        round(recall, 2)
    )

    print(
        "Precision@3:",
        round(precision, 2)
    )