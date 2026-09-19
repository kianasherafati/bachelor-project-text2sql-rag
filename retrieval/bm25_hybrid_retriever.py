"""Controlled BM25 experiment over the frozen original lexical content.

The BM25 documents contain only the normalized physical table, schema, and
own-column identifier tokens already built by the frozen hybrid retriever.
No ERP business aliases or other vocabulary sources are loaded.
"""

from collections import Counter
import math

from graph_expanded_retriever import (
    HYBRID_SEED_COUNT,
    build_outgoing_adjacency,
    rank_expanded_candidates,
)
from hybrid_retriever import (
    DENSE_WEIGHT,
    LEXICAL_WEIGHT,
    HybridSchemaRetriever,
    normalize_tokens,
)


BM25_K1 = 1.5
BM25_B = 0.75


def flatten_lexical_record(record):
    """Flatten exactly the original table/schema/own-column token content."""
    tokens = list(record["table_tokens"])
    tokens.extend(record["schema_tokens"])
    for column_tokens in record["column_tokens"]:
        tokens.extend(column_tokens)
    return tokens


class BM25HybridSchemaRetriever(HybridSchemaRetriever):
    """Separate BM25 path that does not override frozen baseline methods."""

    def __init__(self):
        super().__init__()
        self.bm25_documents = [
            flatten_lexical_record(record)
            for record in self.lexical_records
        ]
        self.bm25_term_frequencies = [
            Counter(tokens) for tokens in self.bm25_documents
        ]
        self.bm25_document_lengths = [
            len(tokens) for tokens in self.bm25_documents
        ]
        self.bm25_average_document_length = (
            sum(self.bm25_document_lengths) / len(self.bm25_document_lengths)
        )
        document_frequency = Counter()
        for frequencies in self.bm25_term_frequencies:
            document_frequency.update(frequencies.keys())
        self.bm25_document_frequency = dict(document_frequency)
        corpus_size = len(self.bm25_documents)
        self.bm25_idf = {
            term: math.log(
                1.0 + (corpus_size - frequency + 0.5) / (frequency + 0.5)
            )
            for term, frequency in self.bm25_document_frequency.items()
        }
        self.outgoing_adjacency = build_outgoing_adjacency(self.documents)
        self._document_index = {
            document["full_name"]: index
            for index, document in enumerate(self.documents)
        }

    def _term_contribution(self, term, document_index):
        frequency = self.bm25_term_frequencies[document_index].get(term, 0)
        if frequency == 0:
            return 0.0
        document_length = self.bm25_document_lengths[document_index]
        denominator = frequency + BM25_K1 * (
            1.0
            - BM25_B
            + BM25_B * document_length / self.bm25_average_document_length
        )
        return self.bm25_idf[term] * (
            frequency * (BM25_K1 + 1.0) / denominator
        )

    def score_bm25(self, question):
        """Return raw and query-max-normalized BM25 scores for all tables."""
        query_frequency = Counter(normalize_tokens(question))
        raw_scores = []
        for index in range(len(self.documents)):
            score = sum(
                count * self._term_contribution(term, index)
                for term, count in query_frequency.items()
                if term in self.bm25_idf
            )
            raw_scores.append(score)
        maximum = max(raw_scores, default=0.0)
        normalized = (
            [score / maximum for score in raw_scores]
            if maximum > 0.0
            else [0.0 for _ in raw_scores]
        )
        return raw_scores, normalized

    def retrieve_bm25_hybrid(self, question, top_k=3):
        """Combine unchanged dense scoring with query-max-normalized BM25."""
        top_k = min(top_k, self.index.ntotal)
        if top_k <= 0:
            return []

        question_embedding = self.embedding_model.encode(
            [question],
            convert_to_numpy=True,
            normalize_embeddings=True,
        ).astype("float32")
        dense_scores, indices = self.index.search(question_embedding, self.index.ntotal)
        raw_bm25, normalized_bm25 = self.score_bm25(question)

        results = []
        for idx, raw_dense_score in zip(indices[0], dense_scores[0]):
            if idx < 0:
                continue
            document = self.documents[idx]
            dense_score = max(0.0, min(1.0, (float(raw_dense_score) + 1.0) / 2.0))
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

    def retrieve_bm25_graph(self, question, top_k=10):
        """Feed BM25Hybrid Top-10 seeds into the frozen graph ranker."""
        if top_k <= 0:
            return {
                "original_bm25_hybrid_top_10": [],
                "expanded_candidate_pool_size": 0,
                "results": [],
            }
        all_bm25_results = self.retrieve_bm25_hybrid(
            question, top_k=self.index.ntotal
        )
        seeds = all_bm25_results[:HYBRID_SEED_COUNT]
        results, pool_size = rank_expanded_candidates(
            all_bm25_results,
            seeds,
            self.outgoing_adjacency,
            min(top_k, self.index.ntotal),
        )
        return {
            "original_bm25_hybrid_top_10": seeds,
            "expanded_candidate_pool_size": pool_size,
            "results": results,
        }

    def bm25_term_details(self, question, full_name):
        """Explain matched BM25 query terms for one physical table."""
        index = self._document_index[full_name]
        query_frequency = Counter(normalize_tokens(question))
        details = []
        for term, query_count in sorted(query_frequency.items()):
            contribution = self._term_contribution(term, index)
            if contribution <= 0.0:
                continue
            details.append({
                "term": term,
                "query_frequency": query_count,
                "document_term_frequency": self.bm25_term_frequencies[index][term],
                "document_frequency": self.bm25_document_frequency[term],
                "idf": self.bm25_idf[term],
                "raw_contribution": query_count * contribution,
            })
        return details

    def lexical_saturation_statistics(self, question, old_lexical_scores):
        """Compare old saturation with BM25 discrimination for one query.

        "Near maximum" means at least 95% of that scorer's query maximum.
        Top-20 spread is maximum minus minimum within its 20 best scores.
        """
        _, bm25_scores = self.score_bm25(question)

        def summarize(scores):
            maximum = max(scores, default=0.0)
            near_threshold = 0.95 * maximum
            ordered = sorted(scores, reverse=True)
            top_20 = ordered[:20]
            return {
                "maximum": maximum,
                "tables_at_maximum": sum(
                    abs(score - maximum) <= 1e-12 for score in scores
                ),
                "tables_near_maximum": sum(
                    score >= near_threshold - 1e-12 for score in scores
                ),
                "top_score_ties": sum(
                    abs(score - maximum) <= 1e-12 for score in scores
                ),
                "top_20_score_spread": (
                    top_20[0] - top_20[-1] if top_20 else 0.0
                ),
                "near_maximum_definition": ">= 95% of query maximum",
            }

        return {
            "old_lexical": summarize(old_lexical_scores),
            "normalized_bm25": summarize(bm25_scores),
            "normalization": "raw_score / maximum_raw_score_for_query",
        }
