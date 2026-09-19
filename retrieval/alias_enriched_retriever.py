"""Metadata-alias retrieval experiment over the frozen retrieval artifacts.

Only the table lexical representation changes: normalized English metadata
aliases are added to the existing table-token set. Dense scoring, lexical
scoring, hybrid weights, and one-hop outgoing-FK graph scoring are reused
unchanged from the frozen baseline modules.
"""

import json
from pathlib import Path

from graph_expanded_retriever import (
    HYBRID_SEED_COUNT,
    build_outgoing_adjacency,
    rank_expanded_candidates,
)
from hybrid_retriever import (
    DENSE_WEIGHT,
    LEXICAL_WEIGHT,
    HybridSchemaRetriever,
    lexical_score,
    normalize_tokens,
)


BASE_DIR = Path(__file__).resolve().parent
ALIAS_CATALOG_PATH = BASE_DIR / "business_alias_catalog.json"


def _normalized_alias_key(value):
    return tuple(normalize_tokens(value, is_identifier=True))


def _column_alias_categories(column, alias):
    """Recover explicit source categories retained on bilingual pair records."""
    alias_key = _normalized_alias_key(alias)
    categories = {
        pair["source_category"]
        for pair in column["explicit_bilingual_pairs"]
        if _normalized_alias_key(pair["english"]) == alias_key
    }
    if not categories:
        # The compact catalog merges unpaired direct-column and form-field
        # strings. Keep that provenance limitation explicit rather than guess.
        categories.add("column_or_form_field_metadata")
    return categories


def build_alias_records(catalog_record):
    """Deduplicate English aliases using the baseline identifier normalizer."""
    records = {}

    def add(value, source_category, column_name=None):
        tokens = _normalized_alias_key(value)
        if not tokens:
            return
        record = records.setdefault(tokens, {
            "alias": value,
            "tokens": list(tokens),
            "source_categories": set(),
            "columns": set(),
        })
        record["source_categories"].add(source_category)
        if column_name is not None:
            record["columns"].add(column_name)

    for alias in catalog_record["table_aliases"]["english"]:
        add(alias, "table_metadata")
    for alias in catalog_record["form_aliases"]["english"]:
        add(alias, "form_metadata")
    for alias in catalog_record["module_aliases"]["english"]:
        add(alias, "module_metadata")
    for column in catalog_record["columns"]:
        for alias in column["english_aliases"]:
            for category in _column_alias_categories(column, alias):
                add(alias, category, column["physical_column_name"])

    results = []
    for tokens in sorted(records):
        record = records[tokens]
        record["source_categories"] = sorted(record["source_categories"])
        record["columns"] = sorted(record["columns"], key=str.casefold)
        results.append(record)
    return results


class AliasEnrichedSchemaRetriever(HybridSchemaRetriever):
    """Separate alias experiment that leaves every baseline method unchanged."""

    def __init__(self):
        super().__init__()
        catalog = json.loads(ALIAS_CATALOG_PATH.read_text(encoding="utf-8"))
        catalog_by_name = {
            record["fully_qualified_table"]: record
            for record in catalog["tables"]
        }
        document_names = {document["full_name"] for document in self.documents}
        if len(catalog_by_name) != 2196 or set(catalog_by_name) != document_names:
            raise ValueError("Alias catalog does not match the indexed corpus")

        self.alias_catalog = catalog
        self.alias_records = []
        self.alias_lexical_records = []
        self.effective_alias_records = []
        for document, original in zip(self.documents, self.lexical_records):
            aliases = build_alias_records(catalog_by_name[document["full_name"]])
            enriched_table_tokens = set(original["table_tokens"])
            for alias in aliases:
                enriched_table_tokens.update(alias["tokens"])
            effective = [
                alias
                for alias in aliases
                if set(alias["tokens"]) - set(original["table_tokens"])
            ]
            self.alias_records.append(aliases)
            self.effective_alias_records.append(effective)
            self.alias_lexical_records.append({
                "table_tokens": sorted(enriched_table_tokens),
                "schema_tokens": list(original["schema_tokens"]),
                "column_tokens": [list(tokens) for tokens in original["column_tokens"]],
            })

        self.outgoing_adjacency = build_outgoing_adjacency(self.documents)
        self._document_index = {
            document["full_name"]: index
            for index, document in enumerate(self.documents)
        }

    def retrieve_alias_hybrid(self, question, top_k=3):
        """Use frozen hybrid scoring with only the lexical records enriched."""
        top_k = min(top_k, self.index.ntotal)
        if top_k <= 0:
            return []

        question_embedding = self.embedding_model.encode(
            [question],
            convert_to_numpy=True,
            normalize_embeddings=True,
        ).astype("float32")
        dense_scores, indices = self.index.search(question_embedding, self.index.ntotal)

        results = []
        for idx, raw_dense_score in zip(indices[0], dense_scores[0]):
            if idx < 0:
                continue
            document = self.documents[idx]
            dense_score = max(0.0, min(1.0, (float(raw_dense_score) + 1.0) / 2.0))
            identifier_score = lexical_score(
                question, self.alias_lexical_records[idx]
            )
            combined_score = (
                DENSE_WEIGHT * dense_score
                + LEXICAL_WEIGHT * identifier_score
            )
            results.append({
                "schema": document["schema"],
                "table_name": document["table_name"],
                "full_name": document["full_name"],
                "dense_score": dense_score,
                "lexical_score": identifier_score,
                "combined_score": combined_score,
                "text": document["text"],
            })
        results.sort(
            key=lambda result: (
                result["combined_score"],
                result["dense_score"],
                result["full_name"],
            ),
            reverse=True,
        )
        return results[:top_k]

    def retrieve_alias_graph(self, question, top_k=10):
        """Feed AliasHybrid seeds into the frozen one-hop graph ranker."""
        if top_k <= 0:
            return {
                "original_alias_hybrid_top_10": [],
                "expanded_candidate_pool_size": 0,
                "results": [],
            }
        all_alias_results = self.retrieve_alias_hybrid(
            question, top_k=self.index.ntotal
        )
        seeds = all_alias_results[:HYBRID_SEED_COUNT]
        results, pool_size = rank_expanded_candidates(
            all_alias_results,
            seeds,
            self.outgoing_adjacency,
            min(top_k, self.index.ntotal),
        )
        return {
            "original_alias_hybrid_top_10": seeds,
            "expanded_candidate_pool_size": pool_size,
            "results": results,
        }

    def alias_evidence(self, question, full_name):
        """Return alias/query matches absent from the original token record."""
        idx = self._document_index[full_name]
        question_tokens = set(normalize_tokens(question))
        original = self.lexical_records[idx]
        original_tokens = set(original["table_tokens"])
        original_tokens.update(original["schema_tokens"])
        for column_tokens in original["column_tokens"]:
            original_tokens.update(column_tokens)

        evidence = []
        for alias in self.alias_records[idx]:
            matched = sorted(
                question_tokens & set(alias["tokens"]) - original_tokens
            )
            if matched:
                evidence.append({
                    "alias": alias["alias"],
                    "matched_new_tokens": matched,
                    "source_categories": alias["source_categories"],
                    "columns": alias["columns"],
                    "interpretation": "supporting_evidence_not_causal_proof",
                })
        return evidence

    def alias_statistics(self):
        counts = [len(records) for records in self.effective_alias_records]
        return {
            "indexed_tables": len(counts),
            "tables_gaining_at_least_one_effective_alias": sum(
                count > 0 for count in counts
            ),
            "average_unique_effective_aliases_per_table": sum(counts) / len(counts),
            "maximum_unique_effective_aliases": max(counts),
            "tables_with_no_effective_added_aliases": sum(count == 0 for count in counts),
        }
