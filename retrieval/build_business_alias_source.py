"""Build a metadata-only ERP business-caption sidecar for indexed tables.

This extractor reads explicit ERP metadata mappings with the configured
read-only connection. It does not read business rows, support tickets, gold
queries, or benchmark questions, and it does not modify retrieval artifacts.
"""

from collections import defaultdict
import json
import pickle
from pathlib import Path
import re
import sys


ROOT = Path(__file__).resolve().parents[1]
RETRIEVAL_DIR = ROOT / "retrieval"
INDEX_METADATA_PATH = RETRIEVAL_DIR / "schema_metadata.pkl"
OUTPUT_PATH = RETRIEVAL_DIR / "business_alias_source.json"
sys.path.insert(0, str(ROOT / "evaluation"))

from validate_text2sql_gold import connect_read_only


PERSIAN_RE = re.compile(r"[\u0600-\u06ff\u0750-\u077f\u08a0-\u08ff]")


def clean_caption(value):
    """Preserve caption contents while treating whitespace-only values as absent."""
    if value is None or not str(value).strip():
        return None
    return str(value)


def language_for_unlabelled_caption(value):
    """Classify the unlabelled tblTable.Comment field by its character script."""
    return "persian" if PERSIAN_RE.search(value) else "english"


def caption_entry(caption, provenance):
    return {"caption": caption, "provenance": [provenance]}


def add_caption(target, language, caption, provenance):
    """Add a caption once and retain all distinct explicit provenance records."""
    caption = clean_caption(caption)
    if caption is None:
        return
    entries = target[language]
    existing = next((item for item in entries if item["caption"] == caption), None)
    if existing is None:
        entries.append(caption_entry(caption, provenance))
    elif provenance not in existing["provenance"]:
        existing["provenance"].append(provenance)


def sorted_captions(captions):
    for language in ("english", "persian"):
        captions[language].sort(key=lambda item: item["caption"].casefold())
        for item in captions[language]:
            item["provenance"].sort(key=lambda value: json.dumps(value, sort_keys=True))
    return captions


def empty_captions():
    return {"english": [], "persian": []}


def fetch_dicts(cursor, statement):
    cursor.execute(statement)
    names = [column[0] for column in cursor.description]
    return [dict(zip(names, row)) for row in cursor.fetchall()]


def load_indexed_tables():
    with INDEX_METADATA_PATH.open("rb") as file:
        documents = pickle.load(file)
    names = [document["full_name"] for document in documents]
    if len(names) != 2196 or len(set(names)) != 2196:
        raise ValueError("Expected exactly 2,196 unique indexed tables")
    return set(names)


def read_metadata():
    """Read only configuration metadata needed for explicit caption mappings."""
    with connect_read_only() as connection:
        cursor = connection.cursor()
        table_rows = fetch_dicts(cursor, """
            SELECT t.ID AS TableMetadataID, t.SchemaName, t.Name, t.Comment
            FROM gnd_egdbm.tblTable AS t
        """)
        form_rows = fetch_dicts(cursor, """
            SELECT
                t.ID AS TableMetadataID,
                t.SchemaName,
                t.Name,
                m.IG AS FormTableMappingID,
                m.FormTypeID,
                m.IsPrimary,
                m.Sequence AS MappingSequence,
                f.CaptionID AS FormCaptionID,
                fc.English AS FormCaptionEnglish,
                fc.Farsi AS FormCaptionPersian,
                f.SystemID,
                s.CaptionID AS SystemCaptionID,
                sc.English AS SystemCaptionEnglish,
                sc.Farsi AS SystemCaptionPersian
            FROM gnd_egdbm.tblTable AS t
            INNER JOIN gnd_egfrm.tblFormTypeTable AS m ON m.TableID = t.ID
            INNER JOIN gnd_egfrm.tblFormType AS f ON f.ID = m.FormTypeID
            LEFT JOIN gnd_egsys.tblCaption AS fc ON fc.ID = f.CaptionID
            LEFT JOIN gnd_egsys.tblSystem AS s ON s.ID = f.SystemID
            LEFT JOIN gnd_egsys.tblCaption AS sc ON sc.ID = s.CaptionID
        """)
        column_rows = fetch_dicts(cursor, """
            SELECT
                t.ID AS TableMetadataID,
                t.SchemaName,
                t.Name,
                tc.ID AS TableColumnID,
                tc.Name AS ColumnName,
                tc.CaptionID AS ColumnCaptionID,
                cc.English AS ColumnCaptionEnglish,
                cc.Farsi AS ColumnCaptionPersian
            FROM gnd_egdbm.tblTable AS t
            INNER JOIN gnd_egdbm.tblTableColumn AS tc ON tc.TableID = t.ID
            LEFT JOIN gnd_egsys.tblCaption AS cc ON cc.ID = tc.CaptionID
        """)
        field_rows = fetch_dicts(cursor, """
            SELECT
                t.ID AS TableMetadataID,
                t.SchemaName,
                t.Name,
                tc.ID AS TableColumnID,
                tc.Name AS ColumnName,
                cdf.ID AS ComponentID,
                c.FormTypeID,
                c.CaptionID AS FieldCaptionID,
                cap.English AS FieldCaptionEnglish,
                cap.Farsi AS FieldCaptionPersian
            FROM gnd_egdbm.tblTable AS t
            INNER JOIN gnd_egdbm.tblTableColumn AS tc ON tc.TableID = t.ID
            INNER JOIN gnd_egfrm.tblComponentDataField AS cdf
                ON cdf.TableColumnID = tc.ID
            INNER JOIN gnd_egfrm.tblComponent AS c ON c.ID = cdf.ID
            LEFT JOIN gnd_egsys.tblCaption AS cap ON cap.ID = c.CaptionID
        """)
    return table_rows, form_rows, column_rows, field_rows


def build_artifact(indexed_tables, metadata):
    table_rows, form_rows, column_rows, field_rows = metadata
    table_lookup = defaultdict(list)
    forms_lookup = defaultdict(list)
    columns_lookup = defaultdict(list)
    fields_lookup = defaultdict(list)

    for rows, lookup in (
        (table_rows, table_lookup),
        (form_rows, forms_lookup),
        (column_rows, columns_lookup),
        (field_rows, fields_lookup),
    ):
        for row in rows:
            full_name = f"{row['SchemaName']}.{row['Name']}"
            if full_name in indexed_tables:
                lookup[full_name].append(row)

    records = []
    for full_name in sorted(indexed_tables, key=str.casefold):
        schema_name, physical_name = full_name.split(".", 1)
        table_captions = empty_captions()
        form_captions = empty_captions()
        module_captions = empty_captions()

        metadata_ids = sorted({
            row["TableMetadataID"] for row in table_lookup[full_name]
        })
        for row in table_lookup[full_name]:
            caption = clean_caption(row["Comment"])
            if caption is not None:
                add_caption(
                    table_captions,
                    language_for_unlabelled_caption(caption),
                    caption,
                    {
                        "source": "table_metadata",
                        "object": "gnd_egdbm.tblTable",
                        "field": "Comment",
                        "table_metadata_id": row["TableMetadataID"],
                    },
                )

        form_mappings = []
        mapping_roles_by_form = defaultdict(set)
        for row in forms_lookup[full_name]:
            form_provenance = {
                "source": "form_metadata",
                "mapping_object": "gnd_egfrm.tblFormTypeTable",
                "caption_object": "gnd_egsys.tblCaption",
                "form_table_mapping_id": row["FormTableMappingID"],
                "form_type_id": row["FormTypeID"],
                "caption_id": row["FormCaptionID"],
            }
            mapping_captions = empty_captions()
            add_caption(mapping_captions, "english", row["FormCaptionEnglish"], form_provenance)
            add_caption(mapping_captions, "persian", row["FormCaptionPersian"], form_provenance)
            add_caption(form_captions, "english", row["FormCaptionEnglish"], form_provenance)
            add_caption(form_captions, "persian", row["FormCaptionPersian"], form_provenance)

            system_provenance = {
                "source": "module_metadata",
                "object": "gnd_egsys.tblSystem",
                "caption_object": "gnd_egsys.tblCaption",
                "system_id": row["SystemID"],
                "caption_id": row["SystemCaptionID"],
                "via_form_type_id": row["FormTypeID"],
            }
            mapping_modules = empty_captions()
            add_caption(mapping_modules, "english", row["SystemCaptionEnglish"], system_provenance)
            add_caption(mapping_modules, "persian", row["SystemCaptionPersian"], system_provenance)
            add_caption(module_captions, "english", row["SystemCaptionEnglish"], system_provenance)
            add_caption(module_captions, "persian", row["SystemCaptionPersian"], system_provenance)

            mapping_role = (
                "primary" if row["IsPrimary"] == 1
                else "detail_or_member" if row["IsPrimary"] == 0
                else None
            )
            if mapping_role is not None:
                mapping_roles_by_form[row["FormTypeID"]].add(mapping_role)
            form_mappings.append({
                "form_table_mapping_id": row["FormTableMappingID"],
                "form_type_id": row["FormTypeID"],
                "is_primary_form_table": (
                    bool(row["IsPrimary"]) if row["IsPrimary"] is not None else None
                ),
                "mapping_role": mapping_role,
                "mapping_sequence": row["MappingSequence"],
                "form_captions": sorted_captions(mapping_captions),
                "module_system_captions": sorted_captions(mapping_modules),
                "provenance": {
                    "source": "form_metadata",
                    "object": "gnd_egfrm.tblFormTypeTable",
                    "table_metadata_id": row["TableMetadataID"],
                },
            })

        column_by_id = {}
        for row in columns_lookup[full_name]:
            column = column_by_id.setdefault(row["TableColumnID"], {
                "physical_column_name": row["ColumnName"],
                "table_column_id": row["TableColumnID"],
                "captions": empty_captions(),
                "form_field_captions": empty_captions(),
                "provenance": {
                    "source": "column_metadata",
                    "object": "gnd_egdbm.tblTableColumn",
                    "table_metadata_id": row["TableMetadataID"],
                },
            })
            direct_provenance = {
                "source": "column_metadata",
                "object": "gnd_egdbm.tblTableColumn",
                "caption_object": "gnd_egsys.tblCaption",
                "table_column_id": row["TableColumnID"],
                "caption_id": row["ColumnCaptionID"],
            }
            add_caption(column["captions"], "english", row["ColumnCaptionEnglish"], direct_provenance)
            add_caption(column["captions"], "persian", row["ColumnCaptionPersian"], direct_provenance)

        for row in fields_lookup[full_name]:
            column = column_by_id.get(row["TableColumnID"])
            if column is None:
                raise ValueError(f"Form-field mapping references an unknown column: {row}")
            provenance = {
                "source": "form_field_metadata",
                "component_object": "gnd_egfrm.tblComponent",
                "data_field_object": "gnd_egfrm.tblComponentDataField",
                "caption_object": "gnd_egsys.tblCaption",
                "component_id": row["ComponentID"],
                "form_type_id": row["FormTypeID"],
                "explicit_table_mapping_roles": sorted(
                    mapping_roles_by_form.get(row["FormTypeID"], set())
                ),
                "table_column_id": row["TableColumnID"],
                "caption_id": row["FieldCaptionID"],
            }
            add_caption(column["form_field_captions"], "english", row["FieldCaptionEnglish"], provenance)
            add_caption(column["form_field_captions"], "persian", row["FieldCaptionPersian"], provenance)

        columns = sorted(column_by_id.values(), key=lambda item: item["physical_column_name"].casefold())
        for column in columns:
            sorted_captions(column["captions"])
            sorted_captions(column["form_field_captions"])
        form_mappings.sort(key=lambda item: (
            item["form_type_id"], item["form_table_mapping_id"]
        ))
        records.append({
            "fully_qualified_table": full_name,
            "physical_table_name": physical_name,
            "schema_name": schema_name,
            "table_metadata_ids": metadata_ids,
            "table_captions": sorted_captions(table_captions),
            "form_captions": sorted_captions(form_captions),
            "module_system_captions": sorted_captions(module_captions),
            "form_mappings": form_mappings,
            "columns": columns,
        })

    return {
        "artifact_type": "erp_business_alias_source",
        "artifact_version": 1,
        "source_database": "GD4_60_SPN",
        "indexed_corpus": {
            "table_count": len(indexed_tables),
            "source": "retrieval/schema_metadata.pkl",
        },
        "content_policy": {
            "metadata_only": True,
            "business_row_data_included": False,
            "support_ticket_text_used": False,
            "benchmark_questions_used": False,
            "captions_translated": False,
            "synonyms_invented": False,
        },
        "tables": records,
    }


def iter_caption_entries(record):
    for category in ("table_captions", "form_captions", "module_system_captions"):
        for language in ("english", "persian"):
            yield from record[category][language]
    for column in record["columns"]:
        for category in ("captions", "form_field_captions"):
            for language in ("english", "persian"):
                yield from column[category][language]


def summarize_and_validate(artifact, indexed_tables):
    records = artifact["tables"]
    emitted = {record["fully_qualified_table"] for record in records}
    if emitted != indexed_tables or len(records) != 2196:
        raise ValueError("Artifact tables do not exactly match the indexed corpus")

    allowed_sources = {
        "table_metadata", "form_metadata", "column_metadata",
        "module_metadata", "form_field_metadata",
    }
    english = set()
    persian = set()
    for record in records:
        for entry in iter_caption_entries(record):
            if not entry["provenance"]:
                raise ValueError("Caption lacks provenance")
            for source in entry["provenance"]:
                if source["source"] not in allowed_sources:
                    raise ValueError(f"Unexpected provenance: {source}")
        for category in ("table_captions", "form_captions", "module_system_captions"):
            english.update(item["caption"] for item in record[category]["english"])
            persian.update(item["caption"] for item in record[category]["persian"])
        for column in record["columns"]:
            for category in ("captions", "form_field_captions"):
                english.update(item["caption"] for item in column[category]["english"])
                persian.update(item["caption"] for item in column[category]["persian"])

    def language_values(record, language):
        values = set()
        for category in ("table_captions", "form_captions", "module_system_captions"):
            values.update(item["caption"] for item in record[category][language])
        for column in record["columns"]:
            for category in ("captions", "form_field_captions"):
                values.update(item["caption"] for item in column[category][language])
        return values

    def has_language(record, language):
        return bool(language_values(record, language))

    def distinct_values(captions):
        return {
            item["caption"]
            for language in ("english", "persian")
            for item in captions[language]
        }

    def ambiguous_bilingual_captions(captions):
        return any(
            len({item["caption"] for item in captions[language]}) > 1
            for language in ("english", "persian")
        )

    multiple_forms = []
    multiple_modules = []
    multiple_field_labels = []
    for record in records:
        if ambiguous_bilingual_captions(record["form_captions"]):
            multiple_forms.append(record["fully_qualified_table"])
        if ambiguous_bilingual_captions(record["module_system_captions"]):
            multiple_modules.append(record["fully_qualified_table"])
        for column in record["columns"]:
            if ambiguous_bilingual_captions(column["form_field_captions"]):
                multiple_field_labels.append(
                    record["fully_qualified_table"] + "." + column["physical_column_name"]
                )

    return {
        "indexed_tables_considered": len(records),
        "tables_with_english_business_caption": sum(has_language(r, "english") for r in records),
        "tables_with_persian_business_caption": sum(has_language(r, "persian") for r in records),
        "tables_with_form_captions": sum(bool(distinct_values(r["form_captions"])) for r in records),
        "tables_with_module_labels": sum(bool(distinct_values(r["module_system_captions"])) for r in records),
        "tables_with_useful_column_captions": sum(any(
            distinct_values(c["captions"]) or distinct_values(c["form_field_captions"])
            for c in r["columns"]
        ) for r in records),
        "unique_english_captions": len(english),
        "unique_persian_captions": len(persian),
        "ambiguous_table_form_caption_mappings": len(multiple_forms),
        "ambiguous_table_module_mappings": len(multiple_modules),
        "ambiguous_column_form_field_mappings": len(multiple_field_labels),
        "ambiguous_table_form_examples": multiple_forms[:10],
        "ambiguous_table_module_examples": multiple_modules[:10],
        "ambiguous_column_form_field_examples": multiple_field_labels[:10],
    }


def main():
    indexed_tables = load_indexed_tables()
    artifact = build_artifact(indexed_tables, read_metadata())
    summary = summarize_and_validate(artifact, indexed_tables)
    OUTPUT_PATH.write_text(
        json.dumps(artifact, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    summary["artifact_bytes"] = OUTPUT_PATH.stat().st_size
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
