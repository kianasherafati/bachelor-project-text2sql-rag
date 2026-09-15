import json
import re
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent

INPUT_PATH = BASE_DIR / "schema.json"
OUTPUT_PATH = BASE_DIR / "schema_documents.json"

ALLOWED_SCHEMA_PREFIXES = ["gnd_"]


def load_schema():
    with INPUT_PATH.open(
        "r",
        encoding="utf-8"
    ) as file:
        return json.load(file)


def filter_tables_for_retrieval(
    schema_data,
    allowed_schema_prefixes=None
):
    if allowed_schema_prefixes is None:
        allowed_schema_prefixes = ALLOWED_SCHEMA_PREFIXES

    normalized_prefixes = tuple(
        prefix.casefold()
        for prefix in allowed_schema_prefixes
    )

    return [
        table
        for table in schema_data["tables"]
        if table["schema"].casefold().startswith(
            normalized_prefixes
        )
    ]


def get_filter_statistics(
    schema_data,
    included_tables
):
    included_schemas = sorted({
        table["schema"]
        for table in included_tables
    })

    return {
        "included_tables": len(included_tables),
        "excluded_tables": (
            len(schema_data["tables"])
            - len(included_tables)
        ),
        "included_schemas": included_schemas,
    }


def humanize_identifier(name):
    """
    Convert CamelCase / PascalCase identifiers into
    space-separated words.

    Examples:
    SalesInvoiceItem -> Sales Invoice Item
    InventoryTransaction -> Inventory Transaction
    UnitPrice -> Unit Price
    """
    return re.sub(
        r"(?<!^)(?=[A-Z])",
        " ",
        name
    )


def format_data_type(column):
    data_type = column["data_type"].lower()

    if data_type in {
        "varchar",
        "nvarchar",
        "char",
        "nchar",
        "binary",
        "varbinary",
    }:
        max_length = column["max_length"]

        if max_length == -1:
            return f"{data_type.upper()}(MAX)"

        return f"{data_type.upper()}({max_length})"

    if data_type in {
        "decimal",
        "numeric",
    }:
        return (
            f"{data_type.upper()}"
            f"({column['precision']},{column['scale']})"
        )

    return data_type.upper()


def get_foreign_key_columns(foreign_key):
    """Return ordered FK columns, including legacy scalar documents."""
    source_columns = foreign_key.get("columns")

    if source_columns is None:
        source_columns = [foreign_key["column"]]

    reference = foreign_key["references"]
    target_columns = reference.get("columns")

    if target_columns is None:
        target_columns = [reference["column"]]

    return source_columns, target_columns


def build_incoming_relationships(schema_data):
    incoming = {}

    for table in schema_data["tables"]:
        for fk in table["foreign_keys"]:
            reference = fk["references"]
            source_columns, target_columns = (
                get_foreign_key_columns(fk)
            )

            target_key = (
                reference["schema"],
                reference["table"],
            )

            incoming.setdefault(
                target_key,
                []
            ).append({
                "source_schema": table["schema"],
                "source_table": table["name"],
                "source_columns": source_columns,
                "target_columns": target_columns,
                "constraint_name": fk["constraint_name"],
            })

    return incoming


def build_table_document(
    table,
    incoming_relationships
):
    schema_name = table["schema"]
    table_name = table["name"]

    table_key = (
        schema_name,
        table_name,
    )

    primary_key_columns = table["primary_key"]
    primary_keys = set(primary_key_columns)

    foreign_key_lookup = {}

    for fk in table["foreign_keys"]:
        source_columns, target_columns = (
            get_foreign_key_columns(fk)
        )

        for source_column, target_column in zip(
            source_columns,
            target_columns
        ):
            foreign_key_lookup.setdefault(
                source_column,
                []
            ).append((fk, target_column))

    lines = []

    # Original table name
    lines.append(
        f"Table: {schema_name}.{table_name}"
    )

    # Human-readable version for embeddings
    lines.append(
        f"Table words: "
        f"{humanize_identifier(table_name)}"
    )

    table_description = table.get("description")

    if table_description and table_description.strip():
        lines.append(
            f"Description: {table_description.strip()}"
        )

    if primary_key_columns:
        lines.append(
            "PRIMARY KEY ("
            + ", ".join(primary_key_columns)
            + ")"
        )

    lines.append("")
    lines.append("Columns:")

    for column in table["columns"]:
        column_name = column["name"]

        humanized_column = (
            humanize_identifier(
                column_name
            )
        )

        formatted_type = format_data_type(
            column
        )

        attributes = []

        if column_name in primary_keys:
            attributes.append(
                "PRIMARY KEY"
            )

        if column["identity"]:
            attributes.append(
                "IDENTITY"
            )

        if column["nullable"]:
            attributes.append(
                "NULL"
            )
        else:
            attributes.append(
                "NOT NULL"
            )

        for fk, target_column in foreign_key_lookup.get(
            column_name,
            []
        ):
            reference = fk["references"]

            attributes.append(
                "FOREIGN KEY REFERENCES "
                f"{reference['schema']}."
                f"{reference['table']}."
                f"{target_column}"
            )

        attribute_text = ", ".join(
            attributes
        )

        lines.append(
            f"- {column_name} "
            f"({humanized_column}) "
            f"{formatted_type} "
            f"[{attribute_text}]"
        )

        column_description = column.get(
            "description"
        )

        if (
            column_description
            and column_description.strip()
        ):
            lines.append(
                "  Description: "
                f"{column_description.strip()}"
            )

    lines.append("")
    lines.append("Relationships:")

    relationship_count = 0

    # Outgoing relationships
    for fk in table["foreign_keys"]:
        reference = fk["references"]
        source_columns, target_columns = (
            get_foreign_key_columns(fk)
        )

        lines.append(
            f"- {fk['constraint_name']}: "
            f"FOREIGN KEY ("
            f"{', '.join(source_columns)}) REFERENCES "
            f"{reference['schema']}."
            f"{reference['table']} ("
            f"{', '.join(target_columns)})."
        )

        relationship_count += 1

    # Incoming relationships
    for relation in incoming_relationships.get(
        table_key,
        []
    ):
        lines.append(
            f"- {relation['constraint_name']}: "
            f"{relation['source_schema']}."
            f"{relation['source_table']} ("
            f"{', '.join(relation['source_columns'])}) "
            f"references {schema_name}.{table_name} ("
            f"{', '.join(relation['target_columns'])})."
        )

        relationship_count += 1

    if relationship_count == 0:
        lines.append(
            "- No foreign-key relationships."
        )

    return "\n".join(lines)


def build_schema_documents(
    schema_data,
    allowed_schema_prefixes=None
):
    included_tables = filter_tables_for_retrieval(
        schema_data,
        allowed_schema_prefixes
    )

    retrieval_schema_data = {
        "tables": included_tables
    }

    incoming_relationships = (
        build_incoming_relationships(
            retrieval_schema_data
        )
    )

    documents = []

    for table in included_tables:
        text = build_table_document(
            table,
            incoming_relationships
        )

        documents.append({
            "schema": table["schema"],
            "table_name": table["name"],
            "full_name": (
                f"{table['schema']}."
                f"{table['name']}"
            ),
            "text": text,
        })

    return documents


def save_documents(
    documents
):
    with OUTPUT_PATH.open(
        "w",
        encoding="utf-8"
    ) as file:
        json.dump(
            documents,
            file,
            ensure_ascii=False,
            indent=2
        )


if __name__ == "__main__":
    schema_data = load_schema()

    documents = build_schema_documents(
        schema_data
    )

    included_tables = filter_tables_for_retrieval(
        schema_data
    )
    statistics = get_filter_statistics(
        schema_data,
        included_tables
    )

    save_documents(
        documents
    )

    print(
        "Schema document generation successful."
    )

    print(
        "Documents generated:",
        len(documents)
    )

    print(
        "Included tables:",
        statistics["included_tables"]
    )
    print(
        "Excluded tables:",
        statistics["excluded_tables"]
    )
    print(
        "Included schemas:",
        ", ".join(statistics["included_schemas"])
        or "(none)"
    )

    print(
        "Output:",
        OUTPUT_PATH
    )

 #   print(
 #       "\nGenerated documents:\n"
 #   )

 #   for document in documents:
 #       print("=" * 70)
 #       print(document["text"])
