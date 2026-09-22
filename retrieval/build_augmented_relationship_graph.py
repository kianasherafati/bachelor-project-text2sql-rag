"""Build the frozen metadata-only augmented relationship graph.

This module deliberately has no benchmark imports. It reads only indexed schema
metadata and the existing explicit ERP form/table mapping artifact.
"""

from __future__ import annotations

from collections import Counter, defaultdict
import hashlib
import json
import math
from pathlib import Path
import pickle
import statistics
import time


ROOT = Path(__file__).resolve().parents[1]
RETRIEVAL = ROOT / "retrieval"
SCHEMA_PATH = ROOT / "schema_extraction" / "schema.json"
INDEX_METADATA_PATH = RETRIEVAL / "schema_metadata.pkl"
FORM_METADATA_PATH = RETRIEVAL / "business_alias_source.json"
OUTPUT_PATH = RETRIEVAL / "augmented_relationship_graph.json"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def ordered_fk_columns(foreign_key):
    child_columns = foreign_key.get("columns") or [foreign_key["column"]]
    reference = foreign_key["references"]
    parent_columns = reference.get("columns") or [reference["column"]]
    return list(child_columns), list(parent_columns)


def add_support(edge_support, source, target, support):
    if source == target:
        return
    edge_support[(source, target)].append(support)


def percentile(values, fraction):
    ordered = sorted(values)
    return ordered[max(0, math.ceil(fraction * len(ordered)) - 1)]


def build_graph():
    started = time.perf_counter()
    with INDEX_METADATA_PATH.open("rb") as handle:
        documents = pickle.load(handle)
    indexed = {document["full_name"] for document in documents}
    if len(documents) != 2196 or len(indexed) != 2196:
        raise RuntimeError("Expected exactly 2,196 unique indexed tables")

    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    aliases = json.loads(FORM_METADATA_PATH.read_text(encoding="utf-8"))
    alias_tables = {item["fully_qualified_table"] for item in aliases["tables"]}
    if alias_tables != indexed:
        raise RuntimeError("Form metadata corpus does not match the indexed corpus")

    edge_support = defaultdict(list)
    outgoing_pairs = set()
    reverse_pairs = set()
    for table in schema["tables"]:
        child = f"{table['schema']}.{table['name']}"
        if child not in indexed:
            continue
        for foreign_key in table["foreign_keys"]:
            reference = foreign_key["references"]
            parent = f"{reference['schema']}.{reference['table']}"
            if parent not in indexed or parent == child:
                continue
            child_columns, parent_columns = ordered_fk_columns(foreign_key)
            common = {
                "constraint_name": foreign_key["constraint_name"],
                "child_table": child,
                "parent_table": parent,
                "child_columns": child_columns,
                "parent_columns": parent_columns,
            }
            outgoing_pairs.add((child, parent))
            reverse_pairs.add((parent, child))
            add_support(edge_support, child, parent, {
                "family": "outgoing_physical_fk",
                "source_type": "declared_physical_fk",
                "edge_direction": "child_to_parent",
                **common,
            })
            add_support(edge_support, parent, child, {
                "family": "reverse_physical_fk",
                "source_type": "reverse_physical_fk",
                "edge_direction": "parent_to_child_retrieval_navigation",
                **common,
            })

    mappings_by_form = defaultdict(list)
    for table in aliases["tables"]:
        for mapping in table["form_mappings"]:
            mappings_by_form[mapping["form_type_id"]].append({
                "table": table["fully_qualified_table"],
                "table_metadata_ids": table["table_metadata_ids"],
                "form_table_mapping_id": mapping["form_table_mapping_id"],
                "is_primary": mapping["is_primary_form_table"],
                "mapping_role": mapping["mapping_role"],
            })

    form_pairs = set()
    multi_table_form_count = 0
    valid_form_count = 0
    for form_type_id, mappings in mappings_by_form.items():
        by_table = defaultdict(list)
        for mapping in mappings:
            by_table[mapping["table"]].append(mapping)
        if len(by_table) > 1:
            multi_table_form_count += 1
        roles_are_unambiguous = all(
            len({entry["is_primary"] for entry in entries}) == 1
            and entries[0]["is_primary"] is not None
            for entries in by_table.values()
        )
        primary_tables = [
            table for table, entries in by_table.items()
            if roles_are_unambiguous and entries[0]["is_primary"] is True
        ]
        if not roles_are_unambiguous or len(primary_tables) != 1:
            continue
        valid_form_count += 1
        primary = primary_tables[0]
        for member, member_mappings in by_table.items():
            if member == primary:
                continue
            primary_mappings = by_table[primary]
            provenance = {
                "family": "explicit_form_association",
                "source_type": "explicit_form_table_mapping",
                "form_type_id": form_type_id,
                "primary_table": primary,
                "member_table": member,
                "primary_mapping_ids": sorted(
                    entry["form_table_mapping_id"] for entry in primary_mappings
                ),
                "member_mapping_ids": sorted(
                    entry["form_table_mapping_id"] for entry in member_mappings
                ),
                "primary_table_metadata_ids": sorted(set().union(*(
                    set(entry["table_metadata_ids"]) for entry in primary_mappings
                ))),
                "member_table_metadata_ids": sorted(set().union(*(
                    set(entry["table_metadata_ids"]) for entry in member_mappings
                ))),
                "association_meaning": "tables belong to the same explicitly mapped form",
            }
            for source, target, direction in (
                (primary, member, "primary_to_member"),
                (member, primary, "member_to_primary"),
            ):
                form_pairs.add((source, target))
                add_support(edge_support, source, target, {
                    **provenance, "edge_direction": direction,
                })

    physical_pairs = outgoing_pairs | reverse_pairs
    combined_pairs = set(edge_support)
    adjacency = Counter(source for source, _ in combined_pairs)
    degrees = [adjacency.get(table, 0) for table in indexed]
    additional_pairs = (reverse_pairs | form_pairs) - outgoing_pairs
    additional_adjacency = Counter(source for source, _ in additional_pairs)

    expected = {
        "outgoing_directed_pairs": 4369,
        "bidirectional_physical_directed_pairs": 8738,
        "form_mapping_rows": 2041,
        "form_type_count": 1427,
        "multi_table_form_type_count": 394,
        "form_association_directed_pairs": 1228,
        "novel_form_association_directed_pairs": 10,
        "combined_directed_pairs": 8748,
        "tables_with_more_than_10_additional_neighbors": 58,
        "maximum_raw_augmented_adjacency": 229,
    }
    actual = {
        "outgoing_directed_pairs": len(outgoing_pairs),
        "reverse_added_directed_pairs": len(reverse_pairs - outgoing_pairs),
        "bidirectional_physical_directed_pairs": len(physical_pairs),
        "form_mapping_rows": sum(len(value) for value in mappings_by_form.values()),
        "form_type_count": len(mappings_by_form),
        "valid_form_type_count": valid_form_count,
        "multi_table_form_type_count": multi_table_form_count,
        "form_association_directed_pairs": len(form_pairs),
        "novel_form_association_directed_pairs": len(form_pairs - physical_pairs),
        "combined_directed_pairs": len(combined_pairs),
        "tables_with_more_than_10_additional_neighbors": sum(
            count > 10 for count in additional_adjacency.values()
        ),
        "maximum_raw_augmented_adjacency": max(degrees),
    }
    mismatches = {
        key: {"expected": value, "actual": actual[key]}
        for key, value in expected.items() if actual[key] != value
    }
    if mismatches:
        raise RuntimeError(f"Structural graph validation failed: {mismatches}")

    records = []
    for source, target in sorted(combined_pairs):
        supports = sorted(
            edge_support[(source, target)],
            key=lambda item: json.dumps(item, sort_keys=True),
        )
        records.append({
            "source": source,
            "target": target,
            "supporting_edge_families": sorted({item["family"] for item in supports}),
            "provenance": supports,
        })

    artifact = {
        "artifact_type": "frozen_bounded_reverse_fk_form_association_graph",
        "artifact_version": 1,
        "corpus_table_count": len(indexed),
        "construction_policy": {
            "benchmark_input_used": False,
            "gold_sql_used": False,
            "ticket_text_used": False,
            "polymorphic_inference_used": False,
            "manual_table_pairs_used": False,
            "self_edges_allowed": False,
        },
        "source_sha256": {
            "retrieval/schema_metadata.pkl": sha256_file(INDEX_METADATA_PATH),
            "schema_extraction/schema.json": sha256_file(SCHEMA_PATH),
            "retrieval/business_alias_source.json": sha256_file(FORM_METADATA_PATH),
        },
        "structural_validation": {
            **actual,
            "expected_measurements": expected,
            "all_expected_measurements_match": True,
            "adjacency": {
                "minimum": min(degrees),
                "median": statistics.median(degrees),
                "mean": statistics.mean(degrees),
                "p95": percentile(degrees, 0.95),
                "p99": percentile(degrees, 0.99),
                "maximum": max(degrees),
            },
        },
        "edges": records,
        "build_seconds": time.perf_counter() - started,
    }
    return artifact


def main():
    if OUTPUT_PATH.exists():
        raise RuntimeError("Frozen graph artifact already exists; refusing to overwrite it")
    artifact = build_graph()
    OUTPUT_PATH.write_text(
        json.dumps(artifact, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({
        "artifact": str(OUTPUT_PATH),
        "sha256": sha256_file(OUTPUT_PATH),
        "bytes": OUTPUT_PATH.stat().st_size,
        "build_seconds": artifact["build_seconds"],
        "structural_validation": artifact["structural_validation"],
    }, indent=2))


if __name__ == "__main__":
    main()
