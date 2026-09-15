import json
import os
from pathlib import Path

import pyodbc
from dotenv import load_dotenv


# ---------------------------------------------------------
# Configuration
# ---------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent
ENV_PATH = BASE_DIR / ".env"
OUTPUT_PATH = BASE_DIR / "schema.json"

load_dotenv(ENV_PATH)

server = os.getenv("DB_SERVER")
database = os.getenv("DB_DATABASE")
driver = os.getenv(
    "DB_DRIVER",
    "ODBC Driver 17 for SQL Server"
)
auth = os.getenv(
    "DB_AUTH",
    "windows"
)


# ---------------------------------------------------------
# Database connection
# ---------------------------------------------------------

def build_connection_string():
    if not server:
        raise ValueError("DB_SERVER is missing from .env")

    if not database:
        raise ValueError("DB_DATABASE is missing from .env")

    if auth == "windows":
        return (
            f"DRIVER={{{driver}}};"
            f"SERVER={server};"
            f"DATABASE={database};"
            "Trusted_Connection=yes;"
            "TrustServerCertificate=yes;"
        )

    if auth == "sql":
        username = os.getenv("DB_USERNAME")
        password = os.getenv("DB_PASSWORD")

        if not username or not password:
            raise ValueError(
                "DB_USERNAME and DB_PASSWORD are required "
                "for SQL authentication."
            )

        return (
            f"DRIVER={{{driver}}};"
            f"SERVER={server};"
            f"DATABASE={database};"
            f"UID={username};"
            f"PWD={password};"
            "TrustServerCertificate=yes;"
        )

    raise ValueError(
        "DB_AUTH must be either 'windows' or 'sql'."
    )


# ---------------------------------------------------------
# Metadata extraction
# ---------------------------------------------------------

def get_tables(cursor):
    cursor.execute("""
        SELECT
            s.name AS schema_name,
            t.name AS table_name,
            CAST(ep.value AS nvarchar(max)) AS description
        FROM sys.tables AS t
        INNER JOIN sys.schemas AS s
            ON t.schema_id = s.schema_id
        LEFT JOIN sys.extended_properties AS ep
            ON ep.class = 1
            AND ep.major_id = t.object_id
            AND ep.minor_id = 0
            AND ep.name = N'MS_Description'
        WHERE t.is_ms_shipped = 0
        ORDER BY
            s.name,
            t.name;
    """)

    return [
        {
            "schema": row.schema_name,
            "name": row.table_name,
            "description": row.description,
            "columns": [],
            "primary_key": [],
            "foreign_keys": []
        }
        for row in cursor.fetchall()
    ]


def get_columns(cursor):
    cursor.execute("""
        SELECT
            s.name AS schema_name,
            t.name AS table_name,
            c.column_id,
            c.name AS column_name,
            ty.name AS data_type,

            CASE
                WHEN ty.name IN ('nvarchar', 'nchar')
                     AND c.max_length > 0
                    THEN c.max_length / 2
                ELSE c.max_length
            END AS max_length,

            c.precision,
            c.scale,
            c.is_nullable,
            c.is_identity,
            CAST(ep.value AS nvarchar(max)) AS description

        FROM sys.tables AS t

        INNER JOIN sys.schemas AS s
            ON t.schema_id = s.schema_id

        INNER JOIN sys.columns AS c
            ON t.object_id = c.object_id

        INNER JOIN sys.types AS ty
            ON c.user_type_id = ty.user_type_id

        LEFT JOIN sys.extended_properties AS ep
            ON ep.class = 1
            AND ep.major_id = t.object_id
            AND ep.minor_id = c.column_id
            AND ep.name = N'MS_Description'

        WHERE t.is_ms_shipped = 0

        ORDER BY
            s.name,
            t.name,
            c.column_id;
    """)

    return cursor.fetchall()


def get_primary_keys(cursor):
    cursor.execute("""
        SELECT
            s.name AS schema_name,
            t.name AS table_name,
            c.name AS column_name,
            ic.key_ordinal

        FROM sys.tables AS t

        INNER JOIN sys.schemas AS s
            ON t.schema_id = s.schema_id

        INNER JOIN sys.indexes AS i
            ON t.object_id = i.object_id

        INNER JOIN sys.index_columns AS ic
            ON i.object_id = ic.object_id
            AND i.index_id = ic.index_id

        INNER JOIN sys.columns AS c
            ON ic.object_id = c.object_id
            AND ic.column_id = c.column_id

        WHERE
            i.is_primary_key = 1
            AND t.is_ms_shipped = 0

        ORDER BY
            s.name,
            t.name,
            ic.key_ordinal;
    """)

    return cursor.fetchall()


def get_foreign_keys(cursor):
    cursor.execute("""
        SELECT
            fk.name AS constraint_name,

            parent_schema.name AS parent_schema,
            parent_table.name AS parent_table,
            parent_column.name AS parent_column,

            referenced_schema.name AS referenced_schema,
            referenced_table.name AS referenced_table,
            referenced_column.name AS referenced_column,
            fkc.constraint_column_id

        FROM sys.foreign_keys AS fk

        INNER JOIN sys.foreign_key_columns AS fkc
            ON fk.object_id = fkc.constraint_object_id

        INNER JOIN sys.tables AS parent_table
            ON fkc.parent_object_id = parent_table.object_id

        INNER JOIN sys.schemas AS parent_schema
            ON parent_table.schema_id = parent_schema.schema_id

        INNER JOIN sys.columns AS parent_column
            ON fkc.parent_object_id = parent_column.object_id
            AND fkc.parent_column_id = parent_column.column_id

        INNER JOIN sys.tables AS referenced_table
            ON fkc.referenced_object_id =
               referenced_table.object_id

        INNER JOIN sys.schemas AS referenced_schema
            ON referenced_table.schema_id =
               referenced_schema.schema_id

        INNER JOIN sys.columns AS referenced_column
            ON fkc.referenced_object_id =
               referenced_column.object_id
            AND fkc.referenced_column_id =
               referenced_column.column_id

        WHERE parent_table.is_ms_shipped = 0

        ORDER BY
            parent_schema.name,
            parent_table.name,
            fk.name,
            fkc.constraint_column_id;
    """)

    foreign_keys = {}

    for row in cursor.fetchall():
        key = (
            row.parent_schema,
            row.parent_table,
            row.constraint_name,
        )

        if key not in foreign_keys:
            foreign_keys[key] = {
                "constraint_name": row.constraint_name,
                "parent_schema": row.parent_schema,
                "parent_table": row.parent_table,
                "columns": [],
                "references": {
                    "schema": row.referenced_schema,
                    "table": row.referenced_table,
                    "columns": [],
                },
            }

        foreign_key = foreign_keys[key]
        foreign_key["columns"].append(row.parent_column)
        foreign_key["references"]["columns"].append(
            row.referenced_column
        )

    return list(foreign_keys.values())


# ---------------------------------------------------------
# Build schema structure
# ---------------------------------------------------------

def extract_schema():
    connection_string = build_connection_string()

    with pyodbc.connect(
        connection_string,
        timeout=5
    ) as connection:

        cursor = connection.cursor()

        tables = get_tables(cursor)
        columns = get_columns(cursor)
        primary_keys = get_primary_keys(cursor)
        foreign_keys = get_foreign_keys(cursor)

    # Fast lookup:
    # ("dbo", "Customer") -> table dictionary
    table_lookup = {
        (table["schema"], table["name"]): table
        for table in tables
    }

    # Add columns
    for row in columns:
        key = (
            row.schema_name,
            row.table_name
        )

        table = table_lookup[key]

        table["columns"].append({
            "name": row.column_name,
            "data_type": row.data_type,
            "max_length": row.max_length,
            "precision": row.precision,
            "scale": row.scale,
            "nullable": bool(row.is_nullable),
            "identity": bool(row.is_identity),
            "description": row.description,
        })

    # Add primary keys
    for row in primary_keys:
        key = (
            row.schema_name,
            row.table_name
        )

        table_lookup[key]["primary_key"].append(
            row.column_name
        )

    # Add foreign keys
    for foreign_key in foreign_keys:
        key = (
            foreign_key["parent_schema"],
            foreign_key["parent_table"]
        )

        table_lookup[key]["foreign_keys"].append({
            "constraint_name": foreign_key["constraint_name"],
            "columns": foreign_key["columns"],

            "references": {
                "schema": foreign_key["references"]["schema"],
                "table": foreign_key["references"]["table"],
                "columns": foreign_key["references"]["columns"],
            }
        })

    schema_data = {
        "database": database,
        "tables": tables
    }

    return schema_data


# ---------------------------------------------------------
# Save JSON
# ---------------------------------------------------------

def save_schema(schema_data):
    with OUTPUT_PATH.open(
        "w",
        encoding="utf-8"
    ) as file:
        json.dump(
            schema_data,
            file,
            ensure_ascii=False,
            indent=2
        )


# ---------------------------------------------------------
# Main
# ---------------------------------------------------------

if __name__ == "__main__":
    schema_data = extract_schema()

    save_schema(schema_data)

    print("Schema extraction successful.")
    print("Database:", schema_data["database"])
    print(
        "Tables extracted:",
        len(schema_data["tables"])
    )
    print("Output:", OUTPUT_PATH)

    print("\nTables:")

    for table in schema_data["tables"]:
        print(
            f"- {table['schema']}.{table['name']}: "
            f"{len(table['columns'])} columns, "
            f"{len(table['primary_key'])} PK columns, "
            f"{len(table['foreign_keys'])} foreign keys"
        )
