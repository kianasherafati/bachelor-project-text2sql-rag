"""Build compact alias and untranslated-caption artifacts from metadata source.

No database, benchmark, ticket, business-row, embedding, index, or retrieval
access is used. Bilingual pairs require a shared explicit metadata identity.
"""

from collections import defaultdict
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE_PATH = ROOT / "retrieval" / "business_alias_source.json"
CATALOG_PATH = ROOT / "retrieval" / "business_alias_catalog.json"
QUEUE_PATH = ROOT / "retrieval" / "business_alias_translation_queue.json"

CATEGORY_LEVELS = {
    "table_metadata": "table/form-level business alias",
    "form_metadata": "table/form-level business alias",
    "module_metadata": "module-level alias",
    "column_metadata": "column/field-level alias",
    "form_field_metadata": "column/field-level alias",
}
LEVEL_PRIORITY = (
    "table/form-level business alias",
    "module-level alias",
    "column/field-level alias",
)


def normalized_text(value):
    """Whitespace normalization only; characters and spelling are unchanged."""
    return " ".join(value.split())


def compact_aliases(*caption_groups, language):
    """Return one original spelling for each whitespace-normalized caption."""
    by_normalized = {}
    for captions in caption_groups:
        for item in captions[language]:
            by_normalized.setdefault(normalized_text(item["caption"]), item["caption"])
    return [by_normalized[key] for key in sorted(by_normalized, key=str.casefold)]


def provenance_identity(source_category, provenance):
    """Return the metadata identity that makes a bilingual pair defensible."""
    if source_category == "table_metadata":
        # tblTable.Comment is a single language-neutral field, so its table ID
        # alone cannot establish that two different strings are translations.
        return None
    if source_category == "form_metadata":
        fields = ("form_table_mapping_id", "form_type_id", "caption_id")
    elif source_category == "module_metadata":
        fields = ("system_id", "caption_id")
    elif source_category == "column_metadata":
        fields = ("table_column_id", "caption_id")
    elif source_category == "form_field_metadata":
        fields = ("component_id", "form_type_id", "table_column_id", "caption_id")
    else:
        raise ValueError(f"Unexpected provenance category: {source_category}")
    identity = {field: provenance.get(field) for field in fields}
    if any(value is None for value in identity.values()):
        return None
    return identity


def explicit_pairs(captions, expected_source):
    """Pair captions only when English and Persian share a metadata identity."""
    concepts = defaultdict(lambda: {"english": {}, "persian": {}})
    identities = {}
    for language in ("english", "persian"):
        for item in captions[language]:
            for provenance in item["provenance"]:
                source = provenance["source"]
                if source != expected_source:
                    raise ValueError(
                        f"Expected {expected_source} provenance, found {source}"
                    )
                identity = provenance_identity(source, provenance)
                if identity is None:
                    continue
                key = json.dumps(identity, sort_keys=True)
                identities[key] = identity
                concepts[key][language].setdefault(
                    normalized_text(item["caption"]), item["caption"]
                )

    pairs = []
    seen = set()
    for key in sorted(concepts):
        concept = concepts[key]
        for english in concept["english"].values():
            for persian in concept["persian"].values():
                pair_key = (
                    normalized_text(english), normalized_text(persian), key
                )
                if pair_key in seen:
                    continue
                seen.add(pair_key)
                pairs.append({
                    "english": english,
                    "persian": persian,
                    "source_category": expected_source,
                    "source_identifier": identities[key],
                    "confidence": "explicit_metadata_pair",
                })
    return pairs


def build_catalog(source):
    records = []
    for table in source["tables"]:
        table_aliases = {
            "english": compact_aliases(table["table_captions"], language="english"),
            "persian": compact_aliases(table["table_captions"], language="persian"),
            "explicit_bilingual_pairs": explicit_pairs(
                table["table_captions"], "table_metadata"
            ),
        }
        form_aliases = {
            "english": compact_aliases(table["form_captions"], language="english"),
            "persian": compact_aliases(table["form_captions"], language="persian"),
            "explicit_bilingual_pairs": explicit_pairs(
                table["form_captions"], "form_metadata"
            ),
        }
        module_aliases = {
            "english": compact_aliases(
                table["module_system_captions"], language="english"
            ),
            "persian": compact_aliases(
                table["module_system_captions"], language="persian"
            ),
            "explicit_bilingual_pairs": explicit_pairs(
                table["module_system_captions"], "module_metadata"
            ),
        }
        columns = []
        for column in table["columns"]:
            column_pairs = explicit_pairs(column["captions"], "column_metadata")
            field_pairs = explicit_pairs(
                column["form_field_captions"], "form_field_metadata"
            )
            columns.append({
                "physical_column_name": column["physical_column_name"],
                "english_aliases": compact_aliases(
                    column["captions"], column["form_field_captions"],
                    language="english",
                ),
                "persian_aliases": compact_aliases(
                    column["captions"], column["form_field_captions"],
                    language="persian",
                ),
                "explicit_bilingual_pairs": column_pairs + field_pairs,
            })
        records.append({
            "fully_qualified_table": table["fully_qualified_table"],
            "physical_table_name": table["physical_table_name"],
            "table_aliases": table_aliases,
            "form_aliases": form_aliases,
            "module_aliases": module_aliases,
            "columns": columns,
        })
    return {
        "artifact_type": "erp_business_alias_catalog",
        "artifact_version": 1,
        "source_artifact": "retrieval/business_alias_source.json",
        "source_sha256": hashlib.sha256(SOURCE_PATH.read_bytes()).hexdigest(),
        "pairing_policy": {
            "confidence": "explicit_metadata_pair",
            "translation_performed": False,
            "cooccurrence_only_pairing_allowed": False,
            "whitespace_normalization_only": True,
        },
        "tables": records,
    }


def caption_occurrences(source):
    """Yield original caption occurrences once per explicit provenance record."""
    for table in source["tables"]:
        full_name = table["fully_qualified_table"]
        form_context = compact_aliases(table["form_captions"], language="english")
        form_context_persian = compact_aliases(
            table["form_captions"], language="persian"
        )
        module_context = compact_aliases(
            table["module_system_captions"], language="english"
        )
        module_context_persian = compact_aliases(
            table["module_system_captions"], language="persian"
        )
        contexts = {
            "form_context": {
                "english": form_context,
                "persian": form_context_persian,
            },
            "module_context": {
                "english": module_context,
                "persian": module_context_persian,
            },
        }
        for captions, category, column_name in (
            (table["table_captions"], "table_metadata", None),
            (table["form_captions"], "form_metadata", None),
            (table["module_system_captions"], "module_metadata", None),
        ):
            for language in ("english", "persian"):
                for item in captions[language]:
                    for provenance in item["provenance"]:
                        yield {
                            "text": item["caption"],
                            "language": language,
                            "source_category": category,
                            "fully_qualified_table": full_name,
                            "physical_column_name": column_name,
                            "provenance": provenance,
                            **contexts,
                        }
        for column in table["columns"]:
            for captions, category in (
                (column["captions"], "column_metadata"),
                (column["form_field_captions"], "form_field_metadata"),
            ):
                for language in ("english", "persian"):
                    for item in captions[language]:
                        for provenance in item["provenance"]:
                            yield {
                                "text": item["caption"],
                                "language": language,
                                "source_category": category,
                                "fully_qualified_table": full_name,
                                "physical_column_name": column["physical_column_name"],
                                "provenance": provenance,
                                **contexts,
                            }


def paired_aliases(catalog):
    paired = {"english": set(), "persian": set()}
    for table in catalog["tables"]:
        groups = [
            table["table_aliases"], table["form_aliases"], table["module_aliases"]
        ] + table["columns"]
        for group in groups:
            for pair in group["explicit_bilingual_pairs"]:
                paired["english"].add(normalized_text(pair["english"]))
                paired["persian"].add(normalized_text(pair["persian"]))
    return paired


def build_unpaired_entries(source, catalog, language):
    paired = paired_aliases(catalog)[language]
    grouped = {}
    seen_occurrences = set()
    for occurrence in caption_occurrences(source):
        if occurrence["language"] != language:
            continue
        normalized = normalized_text(occurrence["text"])
        if normalized in paired:
            continue
        provenance_key = json.dumps(occurrence["provenance"], sort_keys=True)
        occurrence_key = (
            normalized,
            occurrence["source_category"],
            occurrence["fully_qualified_table"],
            occurrence["physical_column_name"],
            provenance_key,
        )
        if occurrence_key in seen_occurrences:
            continue
        seen_occurrences.add(occurrence_key)
        entry = grouped.setdefault(normalized, {
            f"{language}_text": occurrence["text"],
            "source_categories": set(),
            "category_memberships": set(),
            "number_of_occurrences": 0,
            "affected_fully_qualified_tables": set(),
            "affected_columns": set(),
            "form_context": {"english": set(), "persian": set()},
            "module_context": {"english": set(), "persian": set()},
        })
        category = occurrence["source_category"]
        entry["source_categories"].add(category)
        entry["category_memberships"].add(CATEGORY_LEVELS[category])
        entry["number_of_occurrences"] += 1
        entry["affected_fully_qualified_tables"].add(
            occurrence["fully_qualified_table"]
        )
        if occurrence["physical_column_name"] is not None:
            entry["affected_columns"].add(
                occurrence["fully_qualified_table"]
                + "."
                + occurrence["physical_column_name"]
            )
        for context_name in ("form_context", "module_context"):
            for context_language in ("english", "persian"):
                entry[context_name][context_language].update(
                    occurrence[context_name][context_language]
                )

    results = []
    for normalized in sorted(grouped, key=str.casefold):
        entry = grouped[normalized]
        memberships = sorted(
            entry["category_memberships"], key=LEVEL_PRIORITY.index
        )
        entry["source_categories"] = sorted(entry["source_categories"])
        entry["category_memberships"] = memberships
        entry["priority_category"] = memberships[0]
        entry["affected_fully_qualified_tables"] = sorted(
            entry["affected_fully_qualified_tables"], key=str.casefold
        )
        entry["affected_columns"] = sorted(
            entry["affected_columns"], key=str.casefold
        )
        for context_name in ("form_context", "module_context"):
            for context_language in ("english", "persian"):
                entry[context_name][context_language] = sorted(
                    entry[context_name][context_language], key=str.casefold
                )
        results.append(entry)
    return results


def build_queue(source, catalog):
    return {
        "artifact_type": "erp_business_alias_translation_queue",
        "artifact_version": 1,
        "source_artifact": "retrieval/business_alias_source.json",
        "source_sha256": hashlib.sha256(SOURCE_PATH.read_bytes()).hexdigest(),
        "policy": {
            "translations_supplied": False,
            "queue_language": "persian",
            "deduplication": "whitespace-normalized Persian text",
            "paired_aliases_excluded": True,
        },
        "persian_to_english_translation_queue": build_unpaired_entries(
            source, catalog, "persian"
        ),
        "english_only_analysis": build_unpaired_entries(
            source, catalog, "english"
        ),
    }


def all_pairs(table):
    groups = [
        table["table_aliases"], table["form_aliases"], table["module_aliases"]
    ] + table["columns"]
    return [pair for group in groups for pair in group["explicit_bilingual_pairs"]]


def all_aliases(table, language):
    values = []
    for category in ("table_aliases", "form_aliases", "module_aliases"):
        values.extend(table[category][language])
    column_key = f"{language}_aliases"
    for column in table["columns"]:
        values.extend(column[column_key])
    return set(map(normalized_text, values))


def validate_and_summarize(source, catalog, queue):
    source_names = [item["fully_qualified_table"] for item in source["tables"]]
    catalog_names = [item["fully_qualified_table"] for item in catalog["tables"]]
    if len(source_names) != 2196 or source_names != catalog_names:
        raise ValueError("Catalog does not exactly preserve the 2,196-table corpus")

    paired = paired_aliases(catalog)
    source_unique = {"english": set(), "persian": set()}
    for occurrence in caption_occurrences(source):
        source_unique[occurrence["language"]].add(
            normalized_text(occurrence["text"])
        )
    queued_persian = {
        normalized_text(item["persian_text"])
        for item in queue["persian_to_english_translation_queue"]
    }
    english_only = {
        normalized_text(item["english_text"])
        for item in queue["english_only_analysis"]
    }
    if paired["persian"] | queued_persian != source_unique["persian"]:
        raise ValueError("Persian paired/queue partition is incomplete")
    if paired["persian"] & queued_persian:
        raise ValueError("A Persian alias is both paired and queued")
    if paired["english"] | english_only != source_unique["english"]:
        raise ValueError("English paired/unpaired partition is incomplete")
    if paired["english"] & english_only:
        raise ValueError("An English alias is both paired and unpaired")

    for table in catalog["tables"]:
        for pair in all_pairs(table):
            if pair["confidence"] != "explicit_metadata_pair":
                raise ValueError("Unexpected confidence label")
            if pair["source_category"] == "table_metadata":
                raise ValueError("Unlabelled table comments must not be paired")

    breakdown = {
        level: sum(
            item["priority_category"] == level
            for item in queue["persian_to_english_translation_queue"]
        )
        for level in LEVEL_PRIORITY
    }
    bilingual_tables = sum(bool(all_pairs(table)) for table in catalog["tables"])
    only_persian = sum(
        bool(all_aliases(table, "persian"))
        and not all_aliases(table, "english")
        for table in catalog["tables"]
    )
    only_english = sum(
        bool(all_aliases(table, "english"))
        and not all_aliases(table, "persian")
        for table in catalog["tables"]
    )
    return {
        "indexed_tables": len(catalog_names),
        "total_unique_persian_aliases": len(source_unique["persian"]),
        "unique_persian_aliases_with_explicit_english_pair": len(paired["persian"]),
        "unique_persian_aliases_requiring_translation": len(queued_persian),
        "translation_queue_breakdown_by_priority": breakdown,
        "unique_english_aliases_without_persian_pair": len(english_only),
        "tables_with_explicit_bilingual_alias": bilingual_tables,
        "tables_with_only_persian_business_labels": only_persian,
        "tables_with_only_english_business_labels": only_english,
    }


def main():
    source = json.loads(SOURCE_PATH.read_text(encoding="utf-8"))
    catalog = build_catalog(source)
    queue = build_queue(source, catalog)
    summary = validate_and_summarize(source, catalog, queue)
    CATALOG_PATH.write_text(
        json.dumps(catalog, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    QUEUE_PATH.write_text(
        json.dumps(queue, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    summary["catalog_bytes"] = CATALOG_PATH.stat().st_size
    summary["translation_queue_bytes"] = QUEUE_PATH.stat().st_size
    print(json.dumps(summary, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()
