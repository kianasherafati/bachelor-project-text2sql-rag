"""Build deterministic compact English table representations for reranking."""

from __future__ import annotations

import hashlib
import json
import math
import pickle
from pathlib import Path
import re
import statistics
import time

from bge_reranker_v2_m3 import (
    DOCUMENT_BUDGET,
    MANIFEST_PATH,
    QUESTION_BUDGET,
    load_tokenizer,
)


BASE_DIR = Path(__file__).resolve().parent
ROOT = BASE_DIR.parent
CATALOG_PATH = BASE_DIR / "business_alias_catalog.json"
SCHEMA_METADATA_PATH = BASE_DIR / "schema_metadata.pkl"
REPRESENTATIONS_PATH = BASE_DIR / "bge_reranker_table_representations.json"
AUDIT_PATH = BASE_DIR / "bge_reranker_representation_audit.json"
REPORT_PATH = BASE_DIR / "bge_reranker_representation_build_report.json"
IDENTITY_PREFLIGHT_PATH = BASE_DIR / "bge_reranker_identity_preflight.json"
SECTION_BUDGETS = {
    "identity": 68,
    "table_labels": 96,
    "associated_forms": 128,
    "modules": 64,
    "columns": 536,
}


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def collapse(value):
    return re.sub(r"\s+", " ", str(value)).strip()


def normalized_unique(values, excluded=()):
    excluded_set = {collapse(value).casefold() for value in excluded}
    by_normalized = {}
    for raw in values:
        value = collapse(raw)
        if not value or value.casefold() in excluded_set:
            continue
        by_normalized.setdefault(value.casefold(), value)
    return sorted(by_normalized.values(), key=lambda value: (value.casefold(), value))


def token_count(tokenizer, text):
    return len(tokenizer.encode(text, add_special_tokens=False))


def identity_text(table):
    full_name = collapse(table["fully_qualified_table"])
    physical = collapse(table["physical_table_name"])
    schema = full_name.split(".", 1)[0]
    return (
        f"Identity: fully-qualified table {full_name}; "
        f"physical table {physical}; schema {schema}"
    )


def caption_section(tokenizer, heading, captions, budget):
    included = []
    omitted = []
    for caption in captions:
        proposed = f"{heading}: " + ("; ".join(included + [caption]) if included else caption)
        if token_count(tokenizer, proposed) <= budget:
            included.append(caption)
        else:
            omitted.append(caption)
    text = f"{heading}: " + ("; ".join(included) if included else "None")
    if token_count(tokenizer, text) > budget:
        raise ValueError(f"Empty {heading} section exceeds its budget")
    return text, included, omitted


def evenly_spaced_indices(n, m):
    if m == 0:
        return []
    if m == 1:
        return [0]
    return [math.floor(i * (n - 1) / (m - 1)) for i in range(m)]


def column_entry(tokenizer, column):
    physical = collapse(column["physical_column_name"])
    captions = normalized_unique(column.get("english_aliases", []), [physical])
    included = []
    omitted = []
    for caption in captions:
        candidate = "; ".join(included + [caption])
        if token_count(tokenizer, candidate) <= 16:
            included.append(caption)
        else:
            omitted.append(caption)
    text = physical
    if included:
        text += " [" + "; ".join(included) + "]"
    return {
        "physical_column_name": physical,
        "text": text,
        "included_captions": included,
        "omitted_captions": omitted,
    }


def columns_section(tokenizer, columns):
    entries = [column_entry(tokenizer, column) for column in sorted(
        columns,
        key=lambda item: (
            collapse(item["physical_column_name"]).casefold(),
            collapse(item["physical_column_name"]),
        ),
    )]
    selected_indices = []
    for m in range(len(entries), -1, -1):
        indices = evenly_spaced_indices(len(entries), m)
        text = "Columns: " + (
            "; ".join(entries[index]["text"] for index in indices)
            if indices else "None"
        )
        if token_count(tokenizer, text) <= SECTION_BUDGETS["columns"]:
            selected_indices = indices
            break
    selected = set(selected_indices)
    text = "Columns: " + (
        "; ".join(entries[index]["text"] for index in selected_indices)
        if selected_indices else "None"
    )
    return text, {
        "included_columns": [entries[index] for index in selected_indices],
        "omitted_columns": [
            entries[index] for index in range(len(entries)) if index not in selected
        ],
        "all_column_count": len(entries),
    }


def build_one(tokenizer, table):
    full_name = collapse(table["fully_qualified_table"])
    physical = collapse(table["physical_table_name"])
    schema = full_name.split(".", 1)[0]
    identity = identity_text(table)
    if token_count(tokenizer, identity) > SECTION_BUDGETS["identity"]:
        raise ValueError(f"Identity does not fit for {full_name}")
    excluded = [full_name, physical, schema]
    table_labels = normalized_unique(table["table_aliases"]["english"], excluded)
    forms = normalized_unique(table["form_aliases"]["english"], excluded)
    modules = normalized_unique(table["module_aliases"]["english"], excluded)
    label_text, label_in, label_out = caption_section(
        tokenizer, "Table labels", table_labels, SECTION_BUDGETS["table_labels"]
    )
    form_text, form_in, form_out = caption_section(
        tokenizer, "Associated forms", forms, SECTION_BUDGETS["associated_forms"]
    )
    module_text, module_in, module_out = caption_section(
        tokenizer, "Modules", modules, SECTION_BUDGETS["modules"]
    )
    column_text, column_audit = columns_section(tokenizer, table["columns"])
    sections = {
        "identity": identity,
        "table_labels": label_text,
        "associated_forms": form_text,
        "modules": module_text,
        "columns": column_text,
    }
    counts = {name: token_count(tokenizer, text) for name, text in sections.items()}
    for name, count in counts.items():
        if count > SECTION_BUDGETS[name]:
            raise ValueError(f"{full_name} {name} exceeds budget")
    representation = "\n".join(sections.values())
    total = token_count(tokenizer, representation)
    if total > DOCUMENT_BUDGET:
        raise ValueError(f"{full_name} document has {total} tokens")
    audit = {
        "fully_qualified_table": full_name,
        "section_token_counts": counts,
        "total_document_tokens": total,
        "included_table_labels": label_in,
        "omitted_table_labels": label_out,
        "included_form_labels": form_in,
        "omitted_form_labels": form_out,
        "included_module_labels": module_in,
        "omitted_module_labels": module_out,
        **column_audit,
        "representation_sha256": sha256_bytes(representation.encode("utf-8")),
    }
    return representation, audit


def benchmark_questions():
    import sys
    sys.path.insert(0, str(ROOT / "evaluation"))
    sys.path.insert(0, str(BASE_DIR))
    from erp_retrieval_benchmark import tests as dev
    from erp_retrieval_heldout_benchmark import tests as held
    from real_world_text2sql_benchmark import tests as real
    return [case["question"] for case in [*dev, *held, *real]]


def main():
    started = time.perf_counter()
    if not MANIFEST_PATH.is_file():
        raise FileNotFoundError("Frozen reranker manifest must exist before representations")
    tokenizer = load_tokenizer()
    question_counts = [token_count(tokenizer, question) for question in benchmark_questions()]
    if len(question_counts) != 42 or max(question_counts) > QUESTION_BUDGET:
        raise RuntimeError(f"Question-budget preflight failed: {question_counts}")
    catalog = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    tables = catalog["tables"]
    with SCHEMA_METADATA_PATH.open("rb") as handle:
        documents = pickle.load(handle)
    indexed = [document["full_name"] for document in documents]
    if len(tables) != 2196 or {t["fully_qualified_table"] for t in tables} != set(indexed):
        raise ValueError("Alias catalog and indexed corpus differ")
    by_name = {table["fully_qualified_table"]: table for table in tables}

    identity_counts = {
        full_name: token_count(tokenizer, identity_text(by_name[full_name]))
        for full_name in indexed
    }
    maximum_identity_tokens = max(identity_counts.values())
    identity_preflight = {
        "status": "passed" if maximum_identity_tokens <= SECTION_BUDGETS["identity"] else "failed",
        "table_count": len(identity_counts),
        "identity_budget": SECTION_BUDGETS["identity"],
        "token_counts": {
            "minimum": min(identity_counts.values()),
            "median": statistics.median(identity_counts.values()),
            "mean": statistics.mean(identity_counts.values()),
            "maximum": maximum_identity_tokens,
        },
        "tables_at_maximum": sorted(
            name for name, count in identity_counts.items()
            if count == maximum_identity_tokens
        ),
        "tables_exceeding_budget": sorted(
            name for name, count in identity_counts.items()
            if count > SECTION_BUDGETS["identity"]
        ),
    }
    IDENTITY_PREFLIGHT_PATH.write_text(
        json.dumps(identity_preflight, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    if identity_preflight["status"] != "passed":
        raise RuntimeError("Identity preflight failed; benchmark scoring must not run")

    representations = []
    audits = []
    for full_name in indexed:
        representation, audit = build_one(tokenizer, by_name[full_name])
        representations.append({
            "fully_qualified_table": full_name,
            "text": representation,
            "token_count": audit["total_document_tokens"],
            "sha256": audit["representation_sha256"],
        })
        audits.append(audit)

    deterministic_representations = []
    deterministic_audits = []
    for full_name in indexed:
        representation, audit = build_one(tokenizer, by_name[full_name])
        deterministic_representations.append(representation)
        deterministic_audits.append(audit)
    if deterministic_representations != [item["text"] for item in representations]:
        raise RuntimeError("Representation construction is not deterministic")
    if deterministic_audits != audits:
        raise RuntimeError("Representation audit construction is not deterministic")
    REPRESENTATIONS_PATH.write_text(
        json.dumps({
            "artifact_type": "bge_reranker_compact_english_table_representations",
            "table_count": len(representations),
            "section_budgets": SECTION_BUDGETS,
            "document_budget": DOCUMENT_BUDGET,
            "tables": representations,
        }, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    AUDIT_PATH.write_text(
        json.dumps({
            "artifact_type": "bge_reranker_representation_audit",
            "table_count": len(audits),
            "tables": audits,
        }, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    token_counts = [item["total_document_tokens"] for item in audits]
    report = {
        "table_count": len(audits),
        "deterministic_rebuild_match": True,
        "build_seconds": time.perf_counter() - started,
        "identity_preflight_sha256": sha256_file(IDENTITY_PREFLIGHT_PATH),
        "question_token_counts": {
            "count": len(question_counts),
            "maximum": max(question_counts),
            "mean": statistics.mean(question_counts),
        },
        "document_token_counts": {
            "minimum": min(token_counts),
            "mean": statistics.mean(token_counts),
            "median": statistics.median(token_counts),
            "maximum": max(token_counts),
        },
        "tables_with_omitted_columns": sum(bool(item["omitted_columns"]) for item in audits),
        "total_included_columns": sum(len(item["included_columns"]) for item in audits),
        "total_omitted_columns": sum(len(item["omitted_columns"]) for item in audits),
        "representations_sha256": sha256_file(REPRESENTATIONS_PATH),
        "audit_sha256": sha256_file(AUDIT_PATH),
        "source_sha256": {
            "schema_metadata.pkl": sha256_file(SCHEMA_METADATA_PATH),
            "business_alias_catalog.json": sha256_file(CATALOG_PATH),
        },
        "artifact_size_bytes": {
            "representations": REPRESENTATIONS_PATH.stat().st_size,
            "audit": AUDIT_PATH.stat().st_size,
        },
    }
    REPORT_PATH.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
