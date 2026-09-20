"""Frozen BGE-M3 dense, hybrid, and one-hop graph experimental retrievers."""

from __future__ import annotations

import json
import pickle
from pathlib import Path
import time

import faiss
import numpy as np
from FlagEmbedding import BGEM3FlagModel

from graph_expanded_retriever import (
    HYBRID_SEED_COUNT,
    build_outgoing_adjacency,
    rank_expanded_candidates,
)
from hybrid_retriever import (
    DENSE_WEIGHT,
    LEXICAL_WEIGHT,
    build_lexical_record,
    lexical_score,
)


BASE_DIR = Path(__file__).resolve().parent
INDEX_PATH = BASE_DIR / "bge_m3_schema.index"
METADATA_PATH = BASE_DIR / "bge_m3_schema_metadata.json"
MANIFEST_PATH = BASE_DIR / "bge_m3_model_manifest.json"
ORIGINAL_METADATA_PATH = BASE_DIR / "schema_metadata.pkl"

MODEL_REPOSITORY = "BAAI/bge-m3"
MODEL_REVISION = "5617a9f61b028005a4858fdac845db406aefb181"
MAX_ENCODED_TOKENS = 8192
EMBEDDING_DIMENSION = 1024
BATCH_SIZE = 1


class BGEM3SchemaRetriever:
    """One-vector BGE-M3 replacement with frozen lexical and graph stages."""

    def __init__(self):
        self.manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
        if self.manifest["resolved_model_revision"] != MODEL_REVISION:
            raise ValueError("BGE-M3 manifest revision mismatch")
        frozen = self.manifest["frozen_encoding"]
        expected = {
            "precision": "float32",
            "device": "cpu",
            "batch_size": BATCH_SIZE,
            "maximum_encoded_tokens_including_special_tokens": MAX_ENCODED_TOKENS,
            "embedding_dimension": EMBEDDING_DIMENSION,
            "dense_only": True,
        }
        for key, value in expected.items():
            if frozen[key] != value:
                raise ValueError(f"Unexpected frozen BGE setting {key}: {frozen[key]}")

        started = time.perf_counter()
        self.embedding_model = BGEM3FlagModel(
            self.manifest["resolved_model_path"],
            devices="cpu",
            use_fp16=False,
            use_bf16=False,
            normalize_embeddings=True,
            pooling_method="cls",
            query_instruction_for_retrieval=None,
            batch_size=BATCH_SIZE,
            query_max_length=MAX_ENCODED_TOKENS,
            passage_max_length=MAX_ENCODED_TOKENS,
            return_dense=True,
            return_sparse=False,
            return_colbert_vecs=False,
            local_files_only=True,
        )
        self.embedding_model.model.float()
        self.embedding_model.model.to("cpu")
        self.embedding_model.model.eval()
        self.model_load_seconds = time.perf_counter() - started

        self.index = faiss.read_index(str(INDEX_PATH))
        self.metadata = json.loads(METADATA_PATH.read_text(encoding="utf-8"))
        with ORIGINAL_METADATA_PATH.open("rb") as handle:
            self.documents = pickle.load(handle)
        mapping = self.metadata["mapping"]
        if self.index.ntotal != 2196 or self.index.d != EMBEDDING_DIMENSION:
            raise ValueError("Unexpected BGE-M3 FAISS shape")
        if len(mapping) != len(self.documents) or len(mapping) != self.index.ntotal:
            raise ValueError("BGE-M3 mapping/index/document count mismatch")
        for vector_id, (item, document) in enumerate(zip(mapping, self.documents)):
            if (
                item["vector_id"] != vector_id
                or item["fully_qualified_table"] != document["full_name"]
            ):
                raise ValueError("BGE-M3 table order differs from original corpus")
        self.lexical_records = [
            build_lexical_record(document) for document in self.documents
        ]
        self.vector_id_by_name = {
            document["full_name"]: index
            for index, document in enumerate(self.documents)
        }
        self.outgoing_adjacency = build_outgoing_adjacency(self.documents)

    def encode_query(self, question: str) -> np.ndarray:
        output = self.embedding_model.encode_queries(
            [question],
            batch_size=BATCH_SIZE,
            max_length=MAX_ENCODED_TOKENS,
            return_dense=True,
            return_sparse=False,
            return_colbert_vecs=False,
        )
        if output["lexical_weights"] is not None or output["colbert_vecs"] is not None:
            raise ValueError("Non-dense BGE-M3 query output was enabled")
        vector = np.asarray(output["dense_vecs"], dtype=np.float32)
        if vector.shape != (1, EMBEDDING_DIMENSION) or not np.isfinite(vector).all():
            raise ValueError("Invalid BGE-M3 query vector")
        norms = np.linalg.norm(vector, axis=1, keepdims=True)
        if np.any(norms == 0.0):
            raise ValueError("Zero BGE-M3 query vector")
        vector /= norms
        return vector

    def warmup(self) -> None:
        self.encode_query("Nonbenchmark warm-up sentence for dense retrieval.")

    def _all_dense_results(self, question: str):
        query_embedding = self.encode_query(question)
        scores, indices = self.index.search(query_embedding, self.index.ntotal)
        results = []
        for rank, (index, raw_score) in enumerate(
            zip(indices[0], scores[0]), start=1
        ):
            if index < 0:
                continue
            document = self.documents[index]
            cosine = float(raw_score)
            results.append({
                "schema": document["schema"],
                "table_name": document["table_name"],
                "full_name": document["full_name"],
                "score": cosine,
                "raw_bge_cosine": cosine,
                "dense_score": max(0.0, min(1.0, (cosine + 1.0) / 2.0)),
                "global_dense_rank": rank,
                "text": document["text"],
            })
        if len(results) != len(self.documents):
            raise ValueError("BGE-M3 dense search did not rank every table")
        return results

    def retrieve_bge_dense(self, question: str, top_k: int = 3):
        if top_k <= 0:
            return []
        return self._all_dense_results(question)[: min(top_k, self.index.ntotal)]

    def retrieve_bge_hybrid(self, question: str, top_k: int = 3):
        if top_k <= 0:
            return []
        results = []
        for dense_result in self._all_dense_results(question):
            vector_id = self.vector_id_by_name[dense_result["full_name"]]
            identifier_score = lexical_score(
                question, self.lexical_records[vector_id]
            )
            item = dict(dense_result)
            item.update({
                "lexical_score": identifier_score,
                "combined_score": (
                    DENSE_WEIGHT * dense_result["dense_score"]
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
        for rank, result in enumerate(results, start=1):
            result["global_hybrid_rank"] = rank
        return results[: min(top_k, self.index.ntotal)]

    def retrieve_bge_graph(self, question: str, top_k: int = 10):
        if top_k <= 0:
            return {
                "original_bge_hybrid_top_10": [],
                "expanded_candidate_pool_size": 0,
                "results": [],
            }
        all_hybrid = self.retrieve_bge_hybrid(
            question, top_k=self.index.ntotal
        )
        seeds = all_hybrid[:HYBRID_SEED_COUNT]
        results, pool_size = rank_expanded_candidates(
            all_hybrid,
            seeds,
            self.outgoing_adjacency,
            min(top_k, self.index.ntotal),
        )
        for rank, result in enumerate(results, start=1):
            result["global_graph_candidate_rank"] = rank
        return {
            "original_bge_hybrid_top_10": seeds,
            "expanded_candidate_pool_size": pool_size,
            "results": results,
        }
