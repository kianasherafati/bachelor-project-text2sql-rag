"""BM25 over the frozen metadata-enriched English alias representation.

This controlled retriever combines two existing experimental paths without
changing either one: ``AliasEnrichedSchemaRetriever`` supplies the English
metadata alias documents, while ``BM25HybridSchemaRetriever`` supplies the
fixed BM25 formula and the original BM25 baseline.  Persian labels,
translations, ticket text, and hand-authored synonyms are never loaded.
"""

from collections import Counter
import math

from alias_enriched_retriever import AliasEnrichedSchemaRetriever
from bm25_hybrid_retriever import (
    BM25_B,
    BM25_K1,
    BM25HybridSchemaRetriever,
    flatten_lexical_record,
)
from graph_expanded_retriever import HYBRID_SEED_COUNT, rank_expanded_candidates
from hybrid_retriever import DENSE_WEIGHT, LEXICAL_WEIGHT, normalize_tokens


class AliasBM25SchemaRetriever(
    AliasEnrichedSchemaRetriever,
    BM25HybridSchemaRetriever,
):
    """Expose frozen baseline, alias, BM25, and Alias+BM25 retrieval paths."""

    def __init__(self):
        # Cooperative MRO initializes one shared dense model/index, the original
        # BM25 state, and exactly the existing alias-enriched representation.
        super().__init__()
        self.alias_bm25_documents = [
            flatten_lexical_record(record)
            for record in self.alias_lexical_records
        ]
        self.alias_bm25_term_frequencies = [
            Counter(tokens) for tokens in self.alias_bm25_documents
        ]
        self.alias_bm25_document_lengths = [
            len(tokens) for tokens in self.alias_bm25_documents
        ]
        self.alias_bm25_average_document_length = (
            sum(self.alias_bm25_document_lengths)
            / len(self.alias_bm25_document_lengths)
        )
        document_frequency = Counter()
        for frequencies in self.alias_bm25_term_frequencies:
            document_frequency.update(frequencies.keys())
        self.alias_bm25_document_frequency = dict(document_frequency)
        corpus_size = len(self.alias_bm25_documents)
        self.alias_bm25_idf = {
            term: math.log(
                1.0 + (corpus_size - frequency + 0.5) / (frequency + 0.5)
            )
            for term, frequency in self.alias_bm25_document_frequency.items()
        }

    def _alias_term_contribution(self, term, document_index):
        frequency = self.alias_bm25_term_frequencies[document_index].get(term, 0)
        if frequency == 0:
            return 0.0
        document_length = self.alias_bm25_document_lengths[document_index]
        denominator = frequency + BM25_K1 * (
            1.0
            - BM25_B
            + BM25_B
            * document_length
            / self.alias_bm25_average_document_length
        )
        return self.alias_bm25_idf[term] * (
            frequency * (BM25_K1 + 1.0) / denominator
        )

    def score_alias_bm25(self, question):
        """Return raw and query-maximum-normalized alias BM25 scores."""
        query_frequency = Counter(normalize_tokens(question))
        raw_scores = []
        for index in range(len(self.documents)):
            score = sum(
                count * self._alias_term_contribution(term, index)
                for term, count in query_frequency.items()
                if term in self.alias_bm25_idf
            )
            raw_scores.append(score)
        maximum = max(raw_scores, default=0.0)
        normalized = (
            [score / maximum for score in raw_scores]
            if maximum > 0.0
            else [0.0 for _ in raw_scores]
        )
        return raw_scores, normalized

    def retrieve_alias_bm25_hybrid(self, question, top_k=3):
        """Combine unchanged dense scores with English-alias BM25 scores."""
        top_k = min(top_k, self.index.ntotal)
        if top_k <= 0:
            return []

        question_embedding = self.embedding_model.encode(
            [question],
            convert_to_numpy=True,
            normalize_embeddings=True,
        ).astype("float32")
        dense_scores, indices = self.index.search(
            question_embedding,
            self.index.ntotal,
        )
        raw_bm25, normalized_bm25 = self.score_alias_bm25(question)

        results = []
        for idx, raw_dense_score in zip(indices[0], dense_scores[0]):
            if idx < 0:
                continue
            document = self.documents[idx]
            dense_score = max(
                0.0,
                min(1.0, (float(raw_dense_score) + 1.0) / 2.0),
            )
            combined_score = (
                DENSE_WEIGHT * dense_score
                + LEXICAL_WEIGHT * normalized_bm25[idx]
            )
            results.append({
                "schema": document["schema"],
                "table_name": document["table_name"],
                "full_name": document["full_name"],
                "dense_score": dense_score,
                "bm25_raw_score": raw_bm25[idx],
                "bm25_score": normalized_bm25[idx],
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

    def retrieve_alias_bm25_graph(self, question, top_k=10):
        """Apply the frozen one-hop outgoing-FK graph ranker."""
        if top_k <= 0:
            return {
                "original_alias_bm25_hybrid_top_10": [],
                "expanded_candidate_pool_size": 0,
                "results": [],
            }
        all_results = self.retrieve_alias_bm25_hybrid(
            question,
            top_k=self.index.ntotal,
        )
        seeds = all_results[:HYBRID_SEED_COUNT]
        results, pool_size = rank_expanded_candidates(
            all_results,
            seeds,
            self.outgoing_adjacency,
            min(top_k, self.index.ntotal),
        )
        return {
            "original_alias_bm25_hybrid_top_10": seeds,
            "expanded_candidate_pool_size": pool_size,
            "results": results,
        }

    def alias_bm25_term_details(self, question, full_name):
        """Explain the fixed Alias-BM25 term contributions for one table."""
        index = self._document_index[full_name]
        query_frequency = Counter(normalize_tokens(question))
        details = []
        for term, query_count in sorted(query_frequency.items()):
            contribution = self._alias_term_contribution(term, index)
            if contribution <= 0.0:
                continue
            details.append({
                "term": term,
                "query_frequency": query_count,
                "document_term_frequency": (
                    self.alias_bm25_term_frequencies[index][term]
                ),
                "document_frequency": self.alias_bm25_document_frequency[term],
                "idf": self.alias_bm25_idf[term],
                "raw_contribution": query_count * contribution,
            })
        return details

    def bm25_alias_evidence(self, question, full_name):
        """Return generic metadata aliases whose added tokens match the query."""
        return self.alias_evidence(question, full_name)

    def bm25_saturation_statistics(self, question):
        """Compare original BM25 and Alias-BM25 discrimination."""
        _, original_scores = self.score_bm25(question)
        _, alias_scores = self.score_alias_bm25(question)

        def summarize(scores):
            maximum = max(scores, default=0.0)
            threshold = 0.95 * maximum
            ordered = sorted(scores, reverse=True)
            top_20 = ordered[:20]
            return {
                "maximum": maximum,
                "tables_at_maximum": sum(
                    abs(score - maximum) <= 1e-12 for score in scores
                ),
                "tables_near_maximum": sum(
                    score >= threshold - 1e-12 for score in scores
                ),
                "top_score_ties": sum(
                    abs(score - maximum) <= 1e-12 for score in scores
                ),
                "top_20_score_spread": (
                    top_20[0] - top_20[-1] if top_20 else 0.0
                ),
            }

        return {
            "bm25_without_aliases": summarize(original_scores),
            "bm25_with_aliases": summarize(alias_scores),
            "near_maximum_definition": ">= 95% of query maximum",
            "normalization": "raw_score / maximum_raw_score_for_query",
        }
