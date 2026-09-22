"""Frozen shared-query retriever for original and business BGE-M3 indexes."""

from __future__ import annotations

import json
import os
from pathlib import Path
import time

os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
os.environ.setdefault("OMP_NUM_THREADS", "8")
os.environ.setdefault("MKL_NUM_THREADS", "8")

import faiss
import numpy as np
import torch
from FlagEmbedding import BGEM3FlagModel


BASE_DIR = Path(__file__).resolve().parent
ORIGINAL_INDEX_PATH = BASE_DIR / "bge_m3_schema.index"
ORIGINAL_METADATA_PATH = BASE_DIR / "bge_m3_schema_metadata.json"
BUSINESS_INDEX_PATH = BASE_DIR / "bge_business_schema.index"
BUSINESS_METADATA_PATH = BASE_DIR / "bge_business_schema_metadata.json"
MANIFEST_PATH = BASE_DIR / "bge_m3_model_manifest.json"
MODEL_REVISION = "5617a9f61b028005a4858fdac845db406aefb181"
MAX_TOKENS = 8192
DIMENSION = 1024
TABLE_COUNT = 2196

torch.set_num_threads(8)
try:
    torch.set_num_interop_threads(1)
except RuntimeError:
    if torch.get_num_interop_threads() != 1:
        raise


class BGEBusinessDenseRetriever:
    def __init__(self):
        manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
        if manifest["resolved_model_revision"] != MODEL_REVISION:
            raise ValueError("Frozen BGE-M3 revision mismatch")
        started = time.perf_counter()
        self.model = BGEM3FlagModel(
            manifest["resolved_model_path"], devices="cpu", use_fp16=False,
            use_bf16=False, normalize_embeddings=True, pooling_method="cls",
            query_instruction_for_retrieval=None, batch_size=1,
            query_max_length=MAX_TOKENS, passage_max_length=MAX_TOKENS,
            return_dense=True, return_sparse=False, return_colbert_vecs=False,
            local_files_only=True,
        )
        self.model.model.float()
        self.model.model.to("cpu")
        self.model.model.eval()
        self.model_load_seconds = time.perf_counter() - started
        self.original_index = faiss.read_index(str(ORIGINAL_INDEX_PATH))
        self.business_index = faiss.read_index(str(BUSINESS_INDEX_PATH))
        original = json.loads(ORIGINAL_METADATA_PATH.read_text(encoding="utf-8"))["mapping"]
        business = json.loads(BUSINESS_METADATA_PATH.read_text(encoding="utf-8"))["mapping"]
        self.original_names = [item["fully_qualified_table"] for item in original]
        self.business_names = [item["fully_qualified_table"] for item in business]
        if self.original_names != self.business_names:
            raise ValueError("Original and business vector mappings differ")
        for index in (self.original_index, self.business_index):
            if index.ntotal != TABLE_COUNT or index.d != DIMENSION:
                raise ValueError("Unexpected BGE index dimensions")

    def encode_query(self, question: str):
        started = time.perf_counter()
        output = self.model.encode_queries(
            [question], batch_size=1, max_length=MAX_TOKENS,
            return_dense=True, return_sparse=False, return_colbert_vecs=False,
        )
        elapsed = time.perf_counter() - started
        if output["lexical_weights"] is not None or output["colbert_vecs"] is not None:
            raise ValueError("Non-dense BGE query output enabled")
        vector = np.asarray(output["dense_vecs"], dtype=np.float32)
        if vector.shape != (1, DIMENSION) or not np.isfinite(vector).all():
            raise ValueError("Invalid BGE query vector")
        norm = np.linalg.norm(vector, axis=1, keepdims=True)
        if np.any(norm == 0):
            raise ValueError("Zero BGE query vector")
        vector /= norm
        return vector, elapsed

    def search(self, index_name: str, query_vector: np.ndarray):
        index = self.original_index if index_name == "original" else self.business_index
        names = self.original_names if index_name == "original" else self.business_names
        started = time.perf_counter()
        scores, indices = index.search(query_vector, TABLE_COUNT)
        elapsed = time.perf_counter() - started
        rows = [{
            "rank": rank,
            "table": names[int(vector_id)],
            "raw_cosine": float(score),
        } for rank, (vector_id, score) in enumerate(zip(indices[0], scores[0]), start=1)]
        if len(rows) != TABLE_COUNT or len({row["table"] for row in rows}) != TABLE_COUNT:
            raise ValueError("Complete BGE ranking is invalid")
        return rows, elapsed

