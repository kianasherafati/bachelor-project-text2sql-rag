from sql_validator import validate_sql


tests = {
    "VALID RAG QUERY": """
```sql
SELECT
    p.ProductID,
    p.ProductName,
    SUM(si.Quantity) AS TotalSalesQuantity
FROM dbo.Product p
JOIN dbo.SalesInvoiceItem si
    ON p.ProductID = si.ProductID
GROUP BY
    p.ProductID,
    p.ProductName
ORDER BY
    TotalSalesQuantity DESC;
```
""",

    "DELETE QUERY": """
DELETE FROM dbo.Product;
""",

    "MULTIPLE STATEMENTS": """
SELECT *
FROM dbo.Product;

SELECT *
FROM dbo.Customer;
""",

    "UNKNOWN TABLE": """
SELECT *
FROM dbo.DoesNotExist;
""",

    "UNKNOWN COLUMN": """
SELECT
    p.Email
FROM dbo.Product p;
""",
}


for test_name, sql in tests.items():
    print("=" * 70)
    print(test_name)

    result = validate_sql(sql)

    print(
        "Status:",
        result["status"]
    )

    print(
        "Valid:",
        result["valid"]
    )

    print(
        "Referenced tables:",
        result["referenced_tables"]
    )

    print(
        "Errors:",
        result["errors"]
    )

    print(
        "Cleaned SQL:"
    )

    print(
        result["cleaned_sql"]
    )

    print()