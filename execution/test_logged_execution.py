import sys
import time
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent


sys.path.insert(
    0,
    str(PROJECT_ROOT / "app_logging")
)


from query_executor import execute_query

from query_logger import (
    create_request_id,
    write_query_log,
)


question = (
    "Show all products ordered by total "
    "sales quantity from highest to lowest."
)


rag_generated_sql = """
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
"""


retrieved_tables = [
    "dbo.Product",
    "dbo.SalesInvoiceItem",
    "dbo.InventoryTransaction",
]


retrieval_scores = [
    0.3907,
    0.3435,
    0.3392,
]


retrieval_time = 0.4274
generation_time = 10.29


# -----------------------------------------
# Execute validated SQL
# -----------------------------------------

total_start = time.perf_counter()

execution_result = execute_query(
    rag_generated_sql
)

local_pipeline_time = (
    time.perf_counter()
    - total_start
)


# -----------------------------------------
# Write log
# -----------------------------------------

request_id = create_request_id()


record = write_query_log(
    request_id=request_id,

    question=question,

    retrieved_tables=
        retrieved_tables,

    retrieval_scores=
        retrieval_scores,

    generated_sql=
        execution_result["sql"],

    validation_status=(
        "valid"
        if execution_result["executed"]
        else "rejected"
    ),

    validation_errors=
        execution_result[
            "validation_errors"
        ],

    execution_status=
        execution_result["status"],

    row_count=
        execution_result["row_count"],

    retrieval_time=
        retrieval_time,

    generation_time=
        generation_time,

    execution_time=
        execution_result[
            "execution_time"
        ],

    total_time=(
        retrieval_time
        + generation_time
        + (
            execution_result[
                "execution_time"
            ]
            or 0
        )
    ),
)


# -----------------------------------------
# Display result
# -----------------------------------------

print("=" * 70)
print("LOGGED END-TO-END TEST")

print(
    "Request ID:",
    request_id
)

print(
    "Status:",
    execution_result["status"]
)

print(
    "Rows:"
)

for row in execution_result["rows"]:
    print(row)

print(
    "Execution time:",
    execution_result[
        "execution_time"
    ]
)

print(
    "Total recorded time:",
    record[
        "total_time_seconds"
    ]
)

print(
    "Log written successfully."
)