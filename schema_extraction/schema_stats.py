import json
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
SCHEMA_PATH = BASE_DIR / "schema.json"


with SCHEMA_PATH.open(
    "r",
    encoding="utf-8"
) as file:
    schema_data = json.load(file)


tables = schema_data["tables"]

table_count = len(tables)

column_count = sum(
    len(table["columns"])
    for table in tables
)

foreign_key_count = sum(
    len(table["foreign_keys"])
    for table in tables
)

tables_with_description = sum(
    1
    for table in tables
    if table.get("description")
)

columns_with_description = sum(
    1
    for table in tables
    for column in table["columns"]
    if column.get("description")
)

tables_over_50_columns = sum(
    1
    for table in tables
    if len(table["columns"]) > 50
)

tables_over_100_columns = sum(
    1
    for table in tables
    if len(table["columns"]) > 100
)

widest_tables = sorted(
    tables,
    key=lambda table: len(table["columns"]),
    reverse=True
)[:10]


print("Database:", schema_data["database"])
print("Tables:", table_count)
print("Columns:", column_count)
print("Foreign keys:", foreign_key_count)

print(
    "Tables with description:",
    tables_with_description
)

print(
    "Columns with description:",
    columns_with_description
)

print(
    "Tables with more than 50 columns:",
    tables_over_50_columns
)

print(
    "Tables with more than 100 columns:",
    tables_over_100_columns
)

print("\nTop 10 widest tables:")

for table in widest_tables:
    print(
        f"{table['schema']}.{table['name']} "
        f"-> {len(table['columns'])} columns"
    )