from query_executor import execute_query


rag_generated_sql = """
```sql
SELECT 
    p.ProductID,
    p.ProductName,
    SUM(si.Quantity) AS TotalSalesQuantity
FROM 
    dbo.Product p
JOIN 
    dbo.SalesInvoiceItem si
    ON p.ProductID = si.ProductID
GROUP BY 
    p.ProductID,
    p.ProductName
ORDER BY 
    TotalSalesQuantity DESC;
```
"""


print("=" * 70)
print("REAL RAG-GENERATED QUERY")

result = execute_query(
    rag_generated_sql
)

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
    "Rows:"
)

for row in result["rows"]:
    print(row)

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

print(
    "\nCleaned SQL:"
)

print(
    result["sql"]
)