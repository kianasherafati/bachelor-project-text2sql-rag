"""Build the frozen column-complete multi-vector schema experiment.

Only the original schema JSON and frozen schema documents are used.  The
builder emits a separate exact-IP FAISS index and deterministic JSON sidecar;
it never reads alias, benchmark, ticket, database, or BM25 inputs.
"""

from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import statistics
import sys
import time

import faiss
from sentence_transformers import SentenceTransformer


BASE_DIR = Path(__file__).resolve().parent
ROOT = BASE_DIR.parent
SCHEMA_JSON_PATH = ROOT / "schema_extraction" / "schema.json"
SCHEMA_DOCUMENTS_PATH = ROOT / "schema_extraction" / "schema_documents.json"
CHUNK_INDEX_PATH = BASE_DIR / "chunked_schema.index"
CHUNK_METADATA_PATH = BASE_DIR / "chunked_schema_metadata.json"
BUILD_REPORT_PATH = BASE_DIR / "chunked_schema_index_build_report.json"
HYPOTHESIS_PATH = ROOT / "evaluation" / "chunked_truncation_hypothesis.json"
PROTECTED_HASHES_PATH = ROOT / "evaluation" / "chunked_protected_hashes_before.json"

EMBEDDING_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
MAX_CONTENT_TOKENS = 240
MAX_ENCODED_TOKENS = 256
EFFECTIVE_ORIGINAL_CONTENT_BOUNDARY = 254

HYPOTHESIS_FIELDS = {
    "gnd_hrprs.tblEmployee": (
        "EmploymentDate",
        "EmploymentEndDate",
        "IsLeaved",
        "ReasonOfLeave",
    ),
    "gnd_hrcio.tblEmployeeShift": ("EndDateStatus",),
    "gnd_scprd.tblPacking": ("PackagingTypeID", "NetWeight"),
    "gnd_amspt.tblFeedbackCheckList": ("SensorValue",),
    "gnd_spgod.tblGood": ("InterweavingID", "LotNumber"),
    "gnd_hrpyr.tblWorkTime": ("RemainedLeave",),
    "gnd_amspt.tblWorkOrder": ("SuggestedExecutionDate",),
    "gnd_firpd.tblBankGuaranty": ("DepositValue",),
}


def sha256_bytes(value):
    return hashlib.sha256(value).hexdigest()


def sha256_text(value):
    return sha256_bytes(value.encode("utf-8"))


def sha256_file(path):
    return sha256_bytes(path.read_bytes())


def protected_paths():
    paths = [
        SCHEMA_JSON_PATH,
        SCHEMA_DOCUMENTS_PATH,
        BASE_DIR / "schema.index",
        BASE_DIR / "schema_metadata.pkl",
        BASE_DIR / "retriever.py",
        BASE_DIR / "hybrid_retriever.py",
        BASE_DIR / "graph_expanded_retriever.py",
        BASE_DIR / "erp_retrieval_benchmark.py",
        BASE_DIR / "erp_retrieval_heldout_benchmark.py",
        ROOT / "evaluation" / "real_world_text2sql_benchmark.py",
    ]
    for name in (
        "alias_enriched_retriever.py",
        "bm25_hybrid_retriever.py",
        "alias_bm25_retriever.py",
        "business_alias_source.json",
        "business_alias_catalog.json",
        "business_alias_translation_queue.json",
    ):
        path = BASE_DIR / name
        if path.exists():
            paths.append(path)
    paths.extend(
        path for path in (ROOT / "evaluation").iterdir()
        if path.is_file() and "gold" in path.name.casefold()
    )
    return sorted(set(paths))


def format_data_type(column):
    data_type = column["data_type"].upper()
    if data_type.casefold() in {
        "varchar", "nvarchar", "char", "nchar", "binary", "varbinary",
    }:
        length = "MAX" if column["max_length"] == -1 else column["max_length"]
        return f"{data_type}({length})"
    if data_type.casefold() in {"decimal", "numeric"}:
        return f"{data_type}({column['precision']},{column['scale']})"
    return data_type


def foreign_key_columns(foreign_key):
    source = foreign_key.get("columns")
    if source is None:
        source = [foreign_key["column"]]
    target = foreign_key["references"].get("columns")
    if target is None:
        target = [foreign_key["references"]["column"]]
    return list(source), list(target)


def identity_header(full_name, schema_name, table_name, section):
    return "\n".join((
        f"Table: {full_name}",
        f"Schema: {schema_name}",
        f"Physical table: {table_name}",
        f"Section: {section}",
    ))


def token_count(tokenizer, text, *, special_tokens=False):
    return len(tokenizer(text, add_special_tokens=special_tokens)["input_ids"])


def assembled_text(header, payloads):
    if not payloads:
        return header
    return header + "\n\n" + "\n\n".join(payloads)


def table_fk_lookup(table):
    lookup = {}
    for foreign_key in table["foreign_keys"]:
        source_columns, target_columns = foreign_key_columns(foreign_key)
        reference = foreign_key["references"]
        for source, target in zip(source_columns, target_columns):
            lookup.setdefault(source, []).append({
                "constraint_name": foreign_key["constraint_name"],
                "source_column": source,
                "target_table": (
                    f"{reference['schema']}.{reference['table']}"
                ),
                "target_column": target,
            })
    return lookup


def column_record(column, primary_keys, fk_lookup):
    attributes = []
    if column["name"] in primary_keys:
        attributes.append("PRIMARY KEY")
    if column["identity"]:
        attributes.append("IDENTITY")
    attributes.append("NULL" if column["nullable"] else "NOT NULL")
    lines = [
        f"Column: {column['name']}",
        f"Type: {format_data_type(column)}",
        f"Attributes: {', '.join(attributes)}",
    ]
    description = column.get("description")
    if description and description.strip():
        lines.append(f"Description: {description.strip()}")
    for mapping in fk_lookup.get(column["name"], []):
        lines.append(
            f"FK -> {mapping['target_table']}.{mapping['target_column']}"
        )
    return "\n".join(lines), list(fk_lookup.get(column["name"], []))


def composite_fk_records(table):
    records = []
    for foreign_key in table["foreign_keys"]:
        source_columns, target_columns = foreign_key_columns(foreign_key)
        if len(source_columns) <= 1:
            continue
        reference = foreign_key["references"]
        mappings = [
            {
                "source_column": source,
                "target_table": f"{reference['schema']}.{reference['table']}",
                "target_column": target,
            }
            for source, target in zip(source_columns, target_columns)
        ]
        text = "\n".join((
            f"Constraint: {foreign_key['constraint_name']}",
            "Composite FK: " + "; ".join(
                f"{item['source_column']} -> "
                f"{item['target_table']}.{item['target_column']}"
                for item in mappings
            ),
        ))
        records.append({
            "constraint_name": foreign_key["constraint_name"],
            "text": text,
            "mappings": mappings,
        })
    return records


def split_oversized_payload(tokenizer, header, prefix, payload):
    """Split exact consecutive character ranges under the token budget."""
    fragments = []
    start = 0
    while start < len(payload):
        low = start + 1
        high = len(payload)
        best = None
        while low <= high:
            middle = (low + high) // 2
            candidate = assembled_text(header, [prefix + payload[start:middle]])
            if token_count(tokenizer, candidate) <= MAX_CONTENT_TOKENS:
                best = middle
                low = middle + 1
            else:
                high = middle - 1
        if best is None:
            raise ValueError("Continuation prefix leaves no payload token capacity")
        fragments.append({
            "text": prefix + payload[start:best],
            "source_char_start": start,
            "source_char_end": best,
            "source_fragment": payload[start:best],
        })
        start = best
    if "".join(item["source_fragment"] for item in fragments) != payload:
        raise ValueError("Oversized payload split did not preserve all source text")
    return fragments


def make_chunk(
    tokenizer,
    document,
    section,
    sequence,
    payloads,
    columns,
    fk_records,
    continuation=None,
):
    header = identity_header(
        document["full_name"], document["schema"], document["table_name"], section
    )
    text = assembled_text(header, payloads)
    content_tokens = token_count(tokenizer, text)
    encoded_tokens = token_count(tokenizer, text, special_tokens=True)
    if content_tokens > MAX_CONTENT_TOKENS or encoded_tokens > MAX_ENCODED_TOKENS:
        raise ValueError(
            f"Chunk exceeds token budget: {document['full_name']} {section} {sequence}"
        )
    return {
        "fully_qualified_table": document["full_name"],
        "schema_name": document["schema"],
        "physical_table_name": document["table_name"],
        "chunk_id": f"{document['full_name']}::{section.casefold()}::{sequence:04d}",
        "section": section,
        "represented_column_names": list(columns),
        "represented_fk_records": list(fk_records),
        "tokenizer_token_count": content_tokens,
        "fully_encoded_token_count": encoded_tokens,
        "source_schema_document_hash": sha256_text(document["text"]),
        "chunk_text_hash": sha256_text(text),
        "continuation": continuation,
        "text": text,
    }


def build_table_chunks(tokenizer, table, document):
    chunks = []
    fk_lookup = table_fk_lookup(table)
    primary_keys = set(table["primary_key"])
    header = identity_header(
        document["full_name"], document["schema"], document["table_name"], "Columns"
    )
    pending_payloads = []
    pending_columns = []
    pending_fks = []
    sequence = 1

    def flush_columns():
        nonlocal pending_payloads, pending_columns, pending_fks, sequence
        if not pending_payloads:
            return
        chunks.append(make_chunk(
            tokenizer, document, "Columns", sequence, pending_payloads,
            pending_columns, pending_fks,
        ))
        sequence += 1
        pending_payloads = []
        pending_columns = []
        pending_fks = []

    for column in table["columns"]:
        record, mappings = column_record(column, primary_keys, fk_lookup)
        single = assembled_text(header, [record])
        if token_count(tokenizer, single) > MAX_CONTENT_TOKENS:
            flush_columns()
            prefix = f"Column continuation: {column['name']}\n"
            fragments = split_oversized_payload(tokenizer, header, prefix, record)
            for part, fragment in enumerate(fragments, start=1):
                chunks.append(make_chunk(
                    tokenizer,
                    document,
                    "Columns",
                    sequence,
                    [fragment["text"]],
                    [column["name"]],
                    mappings,
                    continuation={
                        "kind": "oversized_column_record",
                        "column_name": column["name"],
                        "part": part,
                        "parts": len(fragments),
                        "source_char_start": fragment["source_char_start"],
                        "source_char_end": fragment["source_char_end"],
                    },
                ))
                sequence += 1
            continue

        candidate_payloads = pending_payloads + [record]
        if (
            pending_payloads
            and token_count(tokenizer, assembled_text(header, candidate_payloads))
            > MAX_CONTENT_TOKENS
        ):
            flush_columns()
        pending_payloads.append(record)
        pending_columns.append(column["name"])
        pending_fks.extend(mappings)
    flush_columns()

    if not table["columns"]:
        chunks.append(make_chunk(
            tokenizer, document, "Columns", sequence, [], [], [],
        ))

    relationship_records = composite_fk_records(table)
    if relationship_records:
        relationship_header = identity_header(
            document["full_name"], document["schema"], document["table_name"],
            "Relationships",
        )
        relationship_payloads = []
        relationship_fks = []
        relationship_sequence = 1

        def flush_relationships():
            nonlocal relationship_payloads, relationship_fks, relationship_sequence
            if not relationship_payloads:
                return
            chunks.append(make_chunk(
                tokenizer, document, "Relationships", relationship_sequence,
                relationship_payloads, [], relationship_fks,
            ))
            relationship_sequence += 1
            relationship_payloads = []
            relationship_fks = []

        for record in relationship_records:
            if token_count(
                tokenizer, assembled_text(relationship_header, [record["text"]])
            ) > MAX_CONTENT_TOKENS:
                flush_relationships()
                prefix = f"Relationship continuation: {record['constraint_name']}\n"
                fragments = split_oversized_payload(
                    tokenizer, relationship_header, prefix, record["text"]
                )
                for part, fragment in enumerate(fragments, start=1):
                    chunks.append(make_chunk(
                        tokenizer, document, "Relationships", relationship_sequence,
                        [fragment["text"]], [], [{
                            "constraint_name": record["constraint_name"],
                            "mappings": record["mappings"],
                        }],
                        continuation={
                            "kind": "oversized_relationship_record",
                            "constraint_name": record["constraint_name"],
                            "part": part,
                            "parts": len(fragments),
                            "source_char_start": fragment["source_char_start"],
                            "source_char_end": fragment["source_char_end"],
                        },
                    ))
                    relationship_sequence += 1
                continue
            candidate = relationship_payloads + [record["text"]]
            if (
                relationship_payloads
                and token_count(
                    tokenizer, assembled_text(relationship_header, candidate)
                ) > MAX_CONTENT_TOKENS
            ):
                flush_relationships()
            relationship_payloads.append(record["text"])
            relationship_fks.append({
                "constraint_name": record["constraint_name"],
                "mappings": record["mappings"],
            })
        flush_relationships()
    return chunks


def build_chunks(tokenizer, schema_data, documents):
    tables = {
        f"{table['schema']}.{table['name']}": table
        for table in schema_data["tables"]
        if table["schema"].casefold().startswith("gnd_")
    }
    document_names = {document["full_name"] for document in documents}
    if len(documents) != 2196 or set(tables) != document_names:
        raise ValueError("Original schema tables do not match the indexed corpus")
    chunks = []
    for document in documents:
        chunks.extend(build_table_chunks(
            tokenizer, tables[document["full_name"]], document
        ))
    return chunks, tables


def build_hypothesis(tokenizer, documents, schema_tables):
    documents_by_name = {item["full_name"]: item for item in documents}
    entries = []
    for table_name, fields in HYPOTHESIS_FIELDS.items():
        document = documents_by_name[table_name]
        available = {item["name"] for item in schema_tables[table_name]["columns"]}
        total_tokens = token_count(tokenizer, document["text"])
        for field in fields:
            if field not in available:
                raise ValueError(f"Hypothesis field absent: {table_name}.{field}")
            marker = f"- {field} "
            character_position = document["text"].find(marker)
            if character_position < 0:
                raise ValueError(f"Field absent from original document: {table_name}.{field}")
            prefix = document["text"][:character_position]
            token_position = token_count(tokenizer, prefix) + 1
            entries.append({
                "table": table_name,
                "field": field,
                "original_table_document_token_count": total_tokens,
                "field_record_start_token_position_1_based": token_position,
                "effective_original_content_boundary": (
                    EFFECTIVE_ORIGINAL_CONTENT_BOUNDARY
                ),
                "falls_beyond_effective_original_embedding_boundary": (
                    token_position > EFFECTIVE_ORIGINAL_CONTENT_BOUNDARY
                ),
                "source_evidence": {
                    "kind": "pre_result_original_document_tokenizer_verification",
                    "schema_document": str(
                        SCHEMA_DOCUMENTS_PATH.relative_to(ROOT)
                    ),
                    "schema_document_sha256": sha256_text(document["text"]),
                    "tokenizer": EMBEDDING_MODEL_NAME,
                    "marker": marker,
                },
            })
    if not all(
        entry["falls_beyond_effective_original_embedding_boundary"]
        for entry in entries
    ):
        raise ValueError("Frozen hypothesis contains a field inside the boundary")
    return {
        "status": "frozen_before_chunked_retrieval_evaluation",
        "embedding_model": EMBEDDING_MODEL_NAME,
        "model_max_sequence_length": 256,
        "effective_original_content_boundary": (
            EFFECTIVE_ORIGINAL_CONTENT_BOUNDARY
        ),
        "method": (
            "Tokenize the frozen original table document without special tokens; "
            "record the 1-based token position at the original column-line marker."
        ),
        "entries": entries,
    }


def validate_chunks(tokenizer, chunks, tables):
    table_counts = Counter(item["fully_qualified_table"] for item in chunks)
    if set(table_counts) != set(tables) or any(count < 1 for count in table_counts.values()):
        raise ValueError("Every indexed table must have at least one chunk")
    represented = {}
    for item in chunks:
        represented.setdefault(item["fully_qualified_table"], set()).update(
            item["represented_column_names"]
        )
        if item["tokenizer_token_count"] > MAX_CONTENT_TOKENS:
            raise ValueError("Content-token budget violation")
        if item["fully_encoded_token_count"] > MAX_ENCODED_TOKENS:
            raise ValueError("Encoded-token budget violation")
        if token_count(tokenizer, item["text"]) != item["tokenizer_token_count"]:
            raise ValueError("Stored token count mismatch")
        if sha256_text(item["text"]) != item["chunk_text_hash"]:
            raise ValueError("Stored chunk hash mismatch")
    missing_columns = {}
    for full_name, table in tables.items():
        expected = {column["name"] for column in table["columns"]}
        missing = expected - represented.get(full_name, set())
        if missing:
            missing_columns[full_name] = sorted(missing)
    if missing_columns:
        raise ValueError(f"Physical columns missing from chunks: {missing_columns}")
    return table_counts


def distribution(values):
    return {
        "minimum": min(values),
        "median": statistics.median(values),
        "mean": statistics.mean(values),
        "maximum": max(values),
    }


def main():
    os.environ.setdefault("HF_HUB_OFFLINE", "1")
    os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
    protected = {
        str(path.relative_to(ROOT)): sha256_file(path)
        for path in protected_paths()
    }
    PROTECTED_HASHES_PATH.write_text(
        json.dumps({
            "status": "recorded_before_chunk_or_index_build",
            "sha256": protected,
        }, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    schema_data = json.loads(SCHEMA_JSON_PATH.read_text(encoding="utf-8"))
    documents = json.loads(SCHEMA_DOCUMENTS_PATH.read_text(encoding="utf-8"))
    model = SentenceTransformer(EMBEDDING_MODEL_NAME, device="cpu")
    tokenizer = model.tokenizer
    if model.max_seq_length != 256:
        raise ValueError(f"Unexpected model max_seq_length: {model.max_seq_length}")

    chunks, tables = build_chunks(tokenizer, schema_data, documents)
    hypothesis = build_hypothesis(tokenizer, documents, tables)
    HYPOTHESIS_PATH.write_text(
        json.dumps(hypothesis, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    frozen_hypothesis_hash = sha256_file(HYPOTHESIS_PATH)

    # Equivalent deterministic second build before any embedding/evaluation.
    rebuilt_chunks, rebuilt_tables = build_chunks(tokenizer, schema_data, documents)
    if tables.keys() != rebuilt_tables.keys() or chunks != rebuilt_chunks:
        raise ValueError("Chunk representation is not deterministic")
    table_counts = validate_chunks(tokenizer, chunks, tables)

    CHUNK_METADATA_PATH.write_text(
        json.dumps({
            "format_version": 1,
            "experiment": "frozen_column_complete_chunked_dense",
            "embedding_model": EMBEDDING_MODEL_NAME,
            "maximum_content_tokens": MAX_CONTENT_TOKENS,
            "payload_overlap": 0,
            "aggregation": "maximum_chunk_cosine_similarity",
            "chunks": chunks,
        }, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    embedding_start = time.perf_counter()
    embeddings = model.encode(
        [item["text"] for item in chunks],
        convert_to_numpy=True,
        normalize_embeddings=True,
        show_progress_bar=True,
    ).astype("float32")
    embedding_seconds = time.perf_counter() - embedding_start
    if embeddings.shape[0] != len(chunks):
        raise ValueError("Embedding count does not match chunk count")

    index_start = time.perf_counter()
    index = faiss.IndexFlatIP(embeddings.shape[1])
    index.add(embeddings)
    faiss.write_index(index, str(CHUNK_INDEX_PATH))
    faiss_seconds = time.perf_counter() - index_start

    content_counts = [item["tokenizer_token_count"] for item in chunks]
    represented_columns = sum(len(table["columns"]) for table in tables.values())
    report = {
        "experiment": "frozen_column_complete_chunked_dense",
        "embedding_model": EMBEDDING_MODEL_NAME,
        "model_max_sequence_length": model.max_seq_length,
        "maximum_content_tokens": MAX_CONTENT_TOKENS,
        "payload_overlap": 0,
        "aggregation": "maximum_chunk_cosine_similarity",
        "total_chunks": len(chunks),
        "tables_represented": len(table_counts),
        "physical_columns_represented": represented_columns,
        "chunk_count_per_table": distribution(list(table_counts.values())),
        "token_count_distribution": distribution(content_counts),
        "continuation_chunks": sum(
            item["continuation"] is not None for item in chunks
        ),
        "relationship_chunks": sum(
            item["section"] == "Relationships" for item in chunks
        ),
        "faiss_vector_count": index.ntotal,
        "faiss_dimension": index.d,
        "index_size_bytes": CHUNK_INDEX_PATH.stat().st_size,
        "chunk_metadata_size_bytes": CHUNK_METADATA_PATH.stat().st_size,
        "embedding_build_seconds": embedding_seconds,
        "faiss_build_seconds": faiss_seconds,
        "deterministic_rebuild_equal": True,
        "zero_embedding_time_truncation": all(
            count <= MAX_CONTENT_TOKENS for count in content_counts
        ),
        "frozen_hypothesis_sha256": frozen_hypothesis_hash,
        "artifact_sha256": {
            str(CHUNK_INDEX_PATH.relative_to(ROOT)): sha256_file(CHUNK_INDEX_PATH),
            str(CHUNK_METADATA_PATH.relative_to(ROOT)): sha256_file(
                CHUNK_METADATA_PATH
            ),
        },
    }
    BUILD_REPORT_PATH.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
