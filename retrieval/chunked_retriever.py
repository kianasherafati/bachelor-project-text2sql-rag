"""Frozen column-complete chunked dense retrieval experiment."""

import json
from pathlib import Path

import faiss

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
)


BASE_DIR = Path(__file__).resolve().parent
CHUNK_INDEX_PATH = BASE_DIR / "chunked_schema.index"
CHUNK_METADATA_PATH = BASE_DIR / "chunked_schema_metadata.json"


class ChunkedSchemaRetriever(HybridSchemaRetriever):
    """Use maximum chunk similarity as the table-level dense score."""

    def __init__(self):
        super().__init__()
        self.chunk_index = faiss.read_index(str(CHUNK_INDEX_PATH))
        metadata = json.loads(CHUNK_METADATA_PATH.read_text(encoding="utf-8"))
        self.chunks = metadata["chunks"]
        if self.chunk_index.ntotal != len(self.chunks):
            raise ValueError("Chunk FAISS vector count does not match metadata")
        if metadata["maximum_content_tokens"] != 240:
            raise ValueError("Unexpected chunk token budget")
        if metadata["payload_overlap"] != 0:
            raise ValueError("Unexpected chunk overlap")
        if metadata["aggregation"] != "maximum_chunk_cosine_similarity":
            raise ValueError("Unexpected chunk aggregation")
        self.documents_by_name = {
            document["full_name"]: document for document in self.documents
        }
        chunk_tables = {
            chunk["fully_qualified_table"] for chunk in self.chunks
        }
        if chunk_tables != set(self.documents_by_name):
            raise ValueError("Chunk tables do not match original indexed tables")
        self.outgoing_adjacency = build_outgoing_adjacency(self.documents)

    def _query_embedding(self, question):
        return self.embedding_model.encode(
            [question],
            convert_to_numpy=True,
            normalize_embeddings=True,
        ).astype("float32")

    def _all_chunked_dense_results(self, question):
        query_embedding = self._query_embedding(question)
        scores, indices = self.chunk_index.search(
            query_embedding,
            self.chunk_index.ntotal,
        )
        winners = {}
        for index, raw_score in zip(indices[0], scores[0]):
            if index < 0:
                continue
            chunk = self.chunks[index]
            full_name = chunk["fully_qualified_table"]
            score = float(raw_score)
            current = winners.get(full_name)
            if current is None or score > current["score"]:
                document = self.documents_by_name[full_name]
                winners[full_name] = {
                    "schema": document["schema"],
                    "table_name": document["table_name"],
                    "full_name": full_name,
                    "score": score,
                    "dense_score": max(0.0, min(1.0, (score + 1.0) / 2.0)),
                    "winning_chunk_id": chunk["chunk_id"],
                    "winning_chunk_section": chunk["section"],
                    "winning_chunk_represented_columns": (
                        chunk["represented_column_names"]
                    ),
                    "winning_chunk_token_count": chunk["tokenizer_token_count"],
                    "text": document["text"],
                }
        if len(winners) != len(self.documents):
            raise ValueError("Chunk aggregation did not produce every table")
        return sorted(
            winners.values(),
            key=lambda result: (result["score"], result["full_name"]),
            reverse=True,
        )

    def retrieve_chunked_dense(self, question, top_k=3):
        top_k = min(top_k, len(self.documents))
        if top_k <= 0:
            return []
        return self._all_chunked_dense_results(question)[:top_k]

    def retrieve_chunked_hybrid(self, question, top_k=3):
        top_k = min(top_k, len(self.documents))
        if top_k <= 0:
            return []
        dense_results = self._all_chunked_dense_results(question)
        lexical_by_name = {
            document["full_name"]: lexical_score(question, record)
            for document, record in zip(self.documents, self.lexical_records)
        }
        results = []
        for result in dense_results:
            identifier_score = lexical_by_name[result["full_name"]]
            item = dict(result)
            item.update({
                "lexical_score": identifier_score,
                "combined_score": (
                    DENSE_WEIGHT * result["dense_score"]
                    + LEXICAL_WEIGHT * identifier_score
                ),
            })
            results.append(item)
        results.sort(
            key=lambda result: (
                result["combined_score"],
                result["dense_score"],
                result["full_name"],
            ),
            reverse=True,
        )
        return results[:top_k]

    def retrieve_chunked_graph(self, question, top_k=10):
        if top_k <= 0:
            return {
                "original_chunked_hybrid_top_10": [],
                "expanded_candidate_pool_size": 0,
                "results": [],
            }
        all_hybrid_results = self.retrieve_chunked_hybrid(
            question,
            top_k=len(self.documents),
        )
        seeds = all_hybrid_results[:HYBRID_SEED_COUNT]
        results, pool_size = rank_expanded_candidates(
            all_hybrid_results,
            seeds,
            self.outgoing_adjacency,
            min(top_k, len(self.documents)),
        )
        return {
            "original_chunked_hybrid_top_10": seeds,
            "expanded_candidate_pool_size": pool_size,
            "results": results,
        }
