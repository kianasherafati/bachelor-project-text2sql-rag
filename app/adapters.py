"""Explicit synthetic fixtures and lazy adapters to existing application modules."""
from app.contracts import SchemaTable

EXAMPLES = {
    "Regional sales": "Show synthetic sales totals by region.",
    "Empty result": "Show synthetic sales with no matches.",
    "Insufficient schema": "Show synthetic supplier risk predictions.",
    "Validation rejected": "Delete synthetic sales records.",
    "Generation error": "Demonstrate a generation error.",
    "Execution error": "Demonstrate an execution error.",
    "Timeout": "Demonstrate a timeout.",
}

SALES_SQL = "SELECT N'تهران' AS Region, 128400 AS SalesTotal\nUNION ALL\nSELECT N'شیراز', 86200\nUNION ALL\nSELECT N'اصفهان', 64750;"
EMPTY_SQL = "SELECT N'' AS Region, 0 AS SalesTotal WHERE 1 = 0;"


class DemoSchemaProvider:
    is_demo = True

    def retrieve(self, question):
        return [SchemaTable(1, "demo.RegionalSales", "Synthetic context: Region (Unicode), SalesTotal (integer). No physical database table.")]

    def rerank(self, question, candidates):
        return list(candidates)


class DemoGenerator:
    is_demo = True

    def generate(self, question, tables):
        if question == EXAMPLES["Generation error"]:
            raise RuntimeError("Synthetic generator failure")
        if question == EXAMPLES["Timeout"]:
            raise TimeoutError()
        if question == EXAMPLES["Validation rejected"]:
            return "DELETE FROM demo.RegionalSales;"
        if question == EXAMPLES["Empty result"]:
            return EMPTY_SQL
        if question == EXAMPLES["Execution error"]:
            return "SELECT 1 / 0 AS SalesTotal;"
        if question == EXAMPLES["Regional sales"]:
            return SALES_SQL
        return "INSUFFICIENT_SCHEMA"


class DemoExecutor:
    is_demo = True

    def __call__(self, sql):
        if sql == "SELECT 1 / 0 AS SalesTotal;":
            return {"status": "execution_error", "execution_error": "Synthetic error"}
        if sql not in (SALES_SQL, EMPTY_SQL):
            raise ValueError("Unsupported synthetic SQL")
        return {"status": "success", "columns": ["Region", "SalesTotal"],
                "rows": [] if sql == EMPTY_SQL else [["تهران", 128400], ["شیراز", 86200], ["اصفهان", 64750]]}


def project_validator(sql):
    from validation.sql_validator import validate_sql
    return validate_sql(sql)


class SQLServerExecutor:
    """Uses the existing validator, row cap, timeouts, and configured DB login.

    Deployment must provision that login as read-only; no permissions are changed.
    """
    is_demo = False

    def __call__(self, sql):
        from execution.query_executor import execute_query
        result = execute_query(sql, max_rows=100)
        # Existing executor returns ODBC failures rather than raising them.
        detail = str(result.get("execution_error") or "").upper()
        if any(code in detail for code in ("HYT00", "HYT01")):
            raise TimeoutError()
        return result
