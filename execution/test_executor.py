from query_executor import execute_query


tests = {
    "VALID SELECT": """
SELECT COUNT(*) AS ProductCount
FROM dbo.Product;
""",

    "VALID EMPTY TABLE SELECT": """
SELECT
    ProductID,
    ProductName
FROM dbo.Product;
""",

    "INVALID UPDATE": """
UPDATE dbo.Product
SET ProductName = 'Test';
""",

    "HALLUCINATED COLUMN": """
SELECT
    Email
FROM dbo.Product;
"""
}


for test_name, sql in tests.items():
    print("=" * 70)
    print(test_name)

    result = execute_query(sql)

    print(
        "Status:",
        result["status"]
    )

    print(
        "Executed:",
        result["executed"]
    )

    print(
        "Columns:",
        result["columns"]
    )

    print(
        "Rows:",
        result["rows"]
    )

    print(
        "Row count:",
        result["row_count"]
    )

    print(
        "Validation errors:",
        result["validation_errors"]
    )

    print(
        "Execution error:",
        result["execution_error"]
    )

    print()