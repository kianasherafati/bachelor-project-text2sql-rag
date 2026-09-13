import json
import pickle
from pathlib import Path

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer


BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent

SCHEMA_DOCUMENTS_PATH = (
    PROJECT_ROOT
    / "schema_extraction"
    / "schema_documents.json"
)

INDEX_PATH = BASE_DIR / "schema.index"
METADATA_PATH = BASE_DIR / "schema_metadata.pkl"

EMBEDDING_MODEL_NAME = (
    "sentence-transformers/all-MiniLM-L6-v2"
)


def load_schema_documents():
    with SCHEMA_DOCUMENTS_PATH.open(
        "r",
        encoding="utf-8"
    ) as file:
        return json.load(file)


def build_index():
    documents = load_schema_documents()

    print(
        "Schema documents loaded:",
        len(documents)
    )

    print(
        "Loading embedding model:",
        EMBEDDING_MODEL_NAME
    )

    model = SentenceTransformer(
        EMBEDDING_MODEL_NAME,
        device="cpu"
    )

    texts = [
        document["text"]
        for document in documents
    ]

    embeddings = model.encode(
        texts,
        convert_to_numpy=True,
        normalize_embeddings=True,
        show_progress_bar=True
    ).astype("float32")

    print(
        "Embeddings shape:",
        embeddings.shape
    )

    dimension = embeddings.shape[1]

    index = faiss.IndexFlatIP(
        dimension
    )

    index.add(
        embeddings
    )

    print(
        "Vectors added to FAISS:",
        index.ntotal
    )

    faiss.write_index(
        index,
        str(INDEX_PATH)
    )

    with METADATA_PATH.open(
        "wb"
    ) as file:
        pickle.dump(
            documents,
            file
        )

    print(
        "FAISS index saved to:",
        INDEX_PATH
    )

    print(
        "Metadata saved to:",
        METADATA_PATH
    )


if __name__ == "__main__":
    build_index()