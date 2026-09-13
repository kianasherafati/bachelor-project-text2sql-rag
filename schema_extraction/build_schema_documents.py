import json
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent

INPUT_PATH = BASE_DIR / "schema.json"
OUTPUT_PATH = BASE_DIR / "schema_documents.json"


def load_schema():
    with INPUT_PATH.open("r", encoding="utf-8") as file:
        return json.load(file)


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


def build_incoming_relationships(schema_data):
    incoming = {}

    for table in schema_data["tables"]:
        for fk in table["foreign_keys"]:
            reference = fk["references"]

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
                "source_column": fk["column"],
                "target_column": reference["column"],
                "constraint_name": fk["constraint_name"],
            })

    return incoming


def build_table_document(table, incoming_relationships):
    schema_name = table["schema"]
    table_name = table["name"]

    table_key = (
        schema_name,
        table_name,
    )

    primary_keys = set(
        table["primary_key"]
    )

    foreign_key_lookup = {
        fk["column"]: fk
        for fk in table["foreign_keys"]
    }

    lines = []

    lines.append(
        f"Table: {schema_name}.{table_name}"
    )

    lines.append("")
    lines.append("Columns:")

    for column in table["columns"]:
        column_name = column["name"]
        formatted_type = format_data_type(
            column
        )

        attributes = []

        if column_name in primary_keys:
            attributes.append("PRIMARY KEY")

        if column["identity"]:
            attributes.append("IDENTITY")

        if column["nullable"]:
            attributes.append("NULL")
        else:
            attributes.append("NOT NULL")

        if column_name in foreign_key_lookup:
            fk = foreign_key_lookup[
                column_name
            ]

            reference = fk["references"]

            attributes.append(
                "FOREIGN KEY REFERENCES "
                f"{reference['schema']}."
                f"{reference['table']}."
                f"{reference['column']}"
            )

        attribute_text = ", ".join(
            attributes
        )

        lines.append(
            f"- {column_name} "
            f"{formatted_type}"
            f" [{attribute_text}]"
        )

    lines.append("")
    lines.append("Relationships:")

    relationship_count = 0

    # Outgoing relationships
    for fk in table["foreign_keys"]:
        reference = fk["references"]

        lines.append(
            f"- {schema_name}.{table_name}."
            f"{fk['column']} references "
            f"{reference['schema']}."
            f"{reference['table']}."
            f"{reference['column']}."
        )

        relationship_count += 1

    # Incoming relationships
    for relation in incoming_relationships.get(
        table_key,
        []
    ):
        lines.append(
            f"- {relation['source_schema']}."
            f"{relation['source_table']}."
            f"{relation['source_column']} "
            f"references "
            f"{schema_name}.{table_name}."
            f"{relation['target_column']}."
        )

        relationship_count += 1

    if relationship_count == 0:
        lines.append(
            "- No foreign-key relationships."
        )

    return "\n".join(lines)


def build_schema_documents(schema_data):
    incoming_relationships = (
        build_incoming_relationships(
            schema_data
        )
    )

    documents = []

    for table in schema_data["tables"]:
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


def save_documents(documents):
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

    save_documents(documents)

    print(
        "Schema document generation successful."
    )

    print(
        "Documents generated:",
        len(documents)
    )

    print(
        "Output:",
        OUTPUT_PATH
    )

    print("\nGenerated documents:\n")

    for document in documents:
        print("=" * 70)
        print(document["text"])