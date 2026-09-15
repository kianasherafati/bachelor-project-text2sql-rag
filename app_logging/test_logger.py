from query_logger import (
    create_request_id,
    write_query_log,
)


request_id = create_request_id()

record = write_query_log(
    request_id=request_id,
    question=(
        "Show all products ordered by total "
        "sales quantity from highest to lowest."
    ),
    retrieved_tables=[
        "dbo.Product",
        "dbo.SalesInvoiceItem",
        "dbo.InventoryTransaction",
    ],
    retrieval_scores=[
        0.3907,
        0.3435,
        0.3392,
    ],
    generated_sql="""
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
""".strip(),
    validation_status="valid",
    validation_errors=[],
    execution_status="success",
    row_count=3,
    retrieval_time=0.4274,
    generation_time=10.29,
    total_time=10.78,
)

print("Log written successfully.")
print("Request ID:", record["request_id"])