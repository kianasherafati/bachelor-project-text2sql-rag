import os
import sys
import time
from pathlib import Path

import pyodbc
from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent


# Allow importing the validator folder
sys.path.insert(
    0,
    str(PROJECT_ROOT / "validation")
)

from sql_validator import validate_sql


ENV_PATH = (
    PROJECT_ROOT
    / "schema_extraction"
    / ".env"
)

load_dotenv(ENV_PATH)


def build_connection_string():
    server = os.getenv("DB_SERVER")
    database = os.getenv("DB_DATABASE")

    driver = os.getenv(
        "DB_DRIVER",
        "ODBC Driver 17 for SQL Server"
    )

    auth = os.getenv(
        "DB_AUTH",
        "sql"
    )

    if not server:
        raise ValueError(
            "DB_SERVER is missing from .env"
        )

    if not database:
        raise ValueError(
            "DB_DATABASE is missing from .env"
        )

    if auth == "sql":
        username = os.getenv(
            "DB_USERNAME"
        )

        password = os.getenv(
            "DB_PASSWORD"
        )

        if not username or not password:
            raise ValueError(
                "DB_USERNAME and DB_PASSWORD "
                "are required."
            )

        return (
            f"DRIVER={{{driver}}};"
            f"SERVER={server};"
            f"DATABASE={database};"
            f"UID={username};"
            f"PWD={password};"
            "TrustServerCertificate=yes;"
        )

    if auth == "windows":
        return (
            f"DRIVER={{{driver}}};"
            f"SERVER={server};"
            f"DATABASE={database};"
            "Trusted_Connection=yes;"
            "TrustServerCertificate=yes;"
        )

    raise ValueError(
        "DB_AUTH must be 'sql' or 'windows'."
    )


def execute_query(
    sql_text,
    max_rows=100
):
    # -----------------------------------------
    # Step 1: Validate generated SQL
    # -----------------------------------------

    validation_result = validate_sql(
        sql_text
    )

    if not validation_result["valid"]:
        return {
            "status": "rejected",
            "executed": False,
            "columns": [],
            "rows": [],
            "row_count": 0,
            "sql": validation_result[
                "cleaned_sql"
            ],
            "validation_errors":
                validation_result["errors"],
            "execution_error": None,
            "execution_time": None,
        }

    cleaned_sql = validation_result[
        "cleaned_sql"
    ]

    connection_string = (
        build_connection_string()
    )

    # -----------------------------------------
    # Step 2: Execute using read-only login
    # -----------------------------------------

    try:
        with pyodbc.connect(
            connection_string,
            timeout=5
        ) as connection:

            # Query execution timeout
            connection.timeout = 10

            cursor = connection.cursor()

            execution_start = (
                time.perf_counter()
            )

            cursor.execute(
                cleaned_sql
            )

            # A valid SELECT should return
            # a result set.
            if cursor.description is None:
                execution_time = (
                    time.perf_counter()
                    - execution_start
                )

                return {
                    "status":
                        "execution_error",
                    "executed": False,
                    "columns": [],
                    "rows": [],
                    "row_count": 0,
                    "sql": cleaned_sql,
                    "validation_errors": [],
                    "execution_error":
                        "Query returned no result set.",
                    "execution_time":
                        execution_time,
                }

            columns = [
                column[0]
                for column
                in cursor.description
            ]

            fetched_rows = (
                cursor.fetchmany(
                    max_rows
                )
            )

            execution_time = (
                time.perf_counter()
                - execution_start
            )

            rows = [
                list(row)
                for row
                in fetched_rows
            ]

            return {
                "status": "success",
                "executed": True,
                "columns": columns,
                "rows": rows,
                "row_count": len(rows),
                "sql": cleaned_sql,
                "validation_errors": [],
                "execution_error": None,
                "execution_time":
                    execution_time,
            }

    except pyodbc.Error as exc:
        return {
            "status": "execution_error",
            "executed": False,
            "columns": [],
            "rows": [],
            "row_count": 0,
            "sql": cleaned_sql,
            "validation_errors": [],
            "execution_error": str(exc),
            "execution_time": None,
        }