import pickle
from pathlib import Path

import faiss
from sentence_transformers import SentenceTransformer


BASE_DIR = Path(__file__).resolve().parent

INDEX_PATH = BASE_DIR / "schema.index"
METADATA_PATH = BASE_DIR / "schema_metadata.pkl"

EMBEDDING_MODEL_NAME = (
    "sentence-transformers/all-MiniLM-L6-v2"
)


class SchemaRetriever:

    def __init__(self):
        print("Loading embedding model...")

        self.embedding_model = SentenceTransformer(
            EMBEDDING_MODEL_NAME,
            device="cpu"
        )

        print("Loading FAISS index...")

        self.index = faiss.read_index(
            str(INDEX_PATH)
        )

        with METADATA_PATH.open(
            "rb"
        ) as file:
            self.documents = pickle.load(file)

        if self.index.ntotal != len(self.documents):
            raise ValueError(
                "FAISS index size does not match metadata count: "
                f"{self.index.ntotal} vectors, "
                f"{len(self.documents)} documents."
            )

        print(
            "Retriever ready. Documents:",
            len(self.documents)
        )

    def retrieve(
        self,
        question,
        top_k=3
    ):
        top_k = min(top_k, self.index.ntotal)

        if top_k <= 0:
            return []

        question_embedding = (
            self.embedding_model.encode(
                [question],
                convert_to_numpy=True,
                normalize_embeddings=True
            ).astype("float32")
        )

        scores, indices = self.index.search(
            question_embedding,
            top_k
        )

        results = []

        for idx, score in zip(
            indices[0],
            scores[0]
        ):
            if idx < 0:
                continue

            document = self.documents[idx]

            results.append({
                "schema": document["schema"],
                "table_name": document["table_name"],
                "full_name": document["full_name"],
                "score": float(score),
                "text": document["text"],
            })

        return results
