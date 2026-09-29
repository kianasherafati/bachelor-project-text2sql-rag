"""Explicit synthetic fixtures and lazy adapters to existing application modules."""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
import json
import os
from pathlib import Path
import re
import sys
from threading import RLock

from app.contracts import SchemaTable


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RETRIEVAL_DIR = PROJECT_ROOT / "retrieval"
RERANKER_REPRESENTATIONS = RETRIEVAL_DIR / "bge_reranker_table_representations.json"
FROZEN_CANDIDATE_DEPTH = 50
FROZEN_FINAL_DEPTH = 10

EXAMPLES = {
    "Regional sales": "Show synthetic sales totals by region.",
    "Empty result": "Show synthetic sales with no matches.",
    "Insufficient schema": "Show synthetic supplier risk predictions.",
    "Validation rejected": "Delete synthetic sales records.",
    "Generation error": "Demonstrate a generation error.",
    "Execution error": "Demonstrate an execution error.",
    "Timeout": "Demonstrate a timeout.",
}

SALES_SQL = "SELECT N'تهران' AS Region, 128400 AS SalesTotal\nUNION ALL\nSELECT N'شیراز', 86200\nUNION ALL\nSELECT N'اصفهان', 64750;"
EMPTY_SQL = "SELECT N'' AS Region, 0 AS SalesTotal WHERE 1 = 0;"


class DemoSchemaProvider:
    is_demo = True

    def retrieve(self, question):
        return [SchemaTable(1, "demo.RegionalSales", "Synthetic context: Region (Unicode), SalesTotal (integer). No physical database table.")]

    def rerank(self, question, candidates):
        return list(candidates)


class DemoGenerator:
    is_demo = True

    def generate(self, question, tables):
        if question == EXAMPLES["Generation error"]:
            raise RuntimeError("Synthetic generator failure")
        if question == EXAMPLES["Timeout"]:
            raise TimeoutError()
        if question == EXAMPLES["Validation rejected"]:
            return "DELETE FROM demo.RegionalSales;"
        if question == EXAMPLES["Empty result"]:
            return EMPTY_SQL
        if question == EXAMPLES["Execution error"]:
            return "SELECT 1 / 0 AS SalesTotal;"
        if question == EXAMPLES["Regional sales"]:
            return SALES_SQL
        return "INSUFFICIENT_SCHEMA"


class DemoExecutor:
    is_demo = True

    def __call__(self, sql):
        if sql == "SELECT 1 / 0 AS SalesTotal;":
            return {"status": "execution_error", "execution_error": "Synthetic error"}
        if sql not in (SALES_SQL, EMPTY_SQL):
            raise ValueError("Unsupported synthetic SQL")
        return {"status": "success", "columns": ["Region", "SalesTotal"],
                "rows": [] if sql == EMPTY_SQL else [["تهران", 128400], ["شیراز", 86200], ["اصفهان", 64750]]}


@dataclass
class FrozenRetrievalResources:
    dense_retriever: object
    graph_retriever: object
    reranker: object
    representations: dict[str, str]


def _load_representations(path=RERANKER_REPRESENTATIONS):
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    tables = payload.get("tables", [])
    representations = {
        item["fully_qualified_table"]: item["text"]
        for item in tables
    }
    if len(representations) != len(tables) or not representations:
        raise ValueError("Frozen reranker representations are empty or contain duplicate tables")
    return representations


@lru_cache(maxsize=1)
def _load_frozen_retrieval_resources():
    """Load the existing frozen components once per application process.

    Imports stay lazy so mock mode never loads model runtimes. The repository's
    frozen modules use sibling imports, so their existing directory must be on
    ``sys.path`` before importing their canonical classes.
    """
    retrieval_path = str(RETRIEVAL_DIR)
    if retrieval_path not in sys.path:
        sys.path.insert(0, retrieval_path)
    os.environ.setdefault("HF_HUB_OFFLINE", "1")
    os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
    os.environ.setdefault("OMP_NUM_THREADS", "8")
    os.environ.setdefault("MKL_NUM_THREADS", "8")

    from bge_m3_retriever import BGEM3SchemaRetriever
    from bge_reranker_v2_m3 import FrozenBGEReranker
    from graph_expanded_retriever import GraphExpandedSchemaRetriever

    # The frozen reranker configures PyTorch determinism during construction;
    # initialize it before either embedding runtime has started worker threads.
    reranker = FrozenBGEReranker()
    return FrozenRetrievalResources(
        dense_retriever=BGEM3SchemaRetriever(),
        graph_retriever=GraphExpandedSchemaRetriever(),
        reranker=reranker,
        representations=_load_representations(),
    )


def _compact_schema_summary(representation, limit=360):
    """Create a presentation-only excerpt without changing reranker input."""
    lines = [line.strip() for line in representation.splitlines() if line.strip()]
    columns = next((line for line in lines if line.startswith("Columns:")), "")
    identity = next((line for line in lines if line.startswith("Identity:")), "")
    summary = " · ".join(value for value in (identity, columns) if value)
    summary = re.sub(r"\s+", " ", summary or representation).strip()
    return summary if len(summary) <= limit else summary[: limit - 1].rstrip() + "…"


class FrozenRetrievalSchemaProvider:
    """Application adapter over the frozen BGE/Graph candidate and reranker path.

    Candidate generation and scoring are delegated unchanged to the canonical
    repository classes. This adapter only deduplicates exact fully-qualified
    identities, maps results to ``SchemaTable``, and enforces the frozen depths.
    """
    is_demo = False

    def __init__(self, resources=None):
        self._injected_resources = resources
        self._lock = RLock()

    def _resources(self):
        return self._injected_resources or _load_frozen_retrieval_resources()

    @staticmethod
    def _name(item):
        name = item.get("full_name")
        if not isinstance(name, str) or "." not in name or not name.strip():
            raise ValueError("Frozen retrieval returned an invalid fully-qualified table")
        return name

    def retrieve(self, question):
        resources = self._resources()
        with self._lock:
            dense = resources.dense_retriever.retrieve_bge_dense(
                question, top_k=FROZEN_CANDIDATE_DEPTH
            )
            graph_run = resources.graph_retriever.retrieve_graph_expanded(
                question, top_k=FROZEN_CANDIDATE_DEPTH
            )
        graph = graph_run["results"]
        if len(dense) != FROZEN_CANDIDATE_DEPTH:
            raise ValueError("Frozen BGE-M3 Dense retrieval did not return Top50")
        if len(graph) > FROZEN_CANDIDATE_DEPTH:
            raise ValueError("Frozen MiniLM Graph retrieval exceeded Top50")

        # This exact-name union mirrors the frozen materialization policy. The
        # alphabetical order is deterministic and has no effect on model scores.
        names = {self._name(item) for item in dense}
        names.update(self._name(item) for item in graph)
        return [
            SchemaTable(rank=rank, name=name)
            for rank, name in enumerate(sorted(names), start=1)
        ]

    def rerank(self, question, candidates):
        resources = self._resources()
        names = [candidate.name for candidate in candidates]
        if len(names) != len(set(names)):
            raise ValueError("Frozen retrieval candidate union contains duplicate tables")
        if len(names) < FROZEN_FINAL_DEPTH:
            raise ValueError("Frozen retrieval produced fewer than ten candidates")

        scored = []
        with self._lock:
            for name in names:
                representation = resources.representations.get(name)
                if representation is None:
                    raise ValueError(f"Missing frozen reranker representation for {name}")
                score, _latency, _pair_tokens = resources.reranker.score(
                    question, representation
                )
                scored.append((name, float(score), representation))

        # Frozen policy: raw logit descending, fully-qualified identity ascending
        # for exact ties, then take the first ten.
        scored.sort(key=lambda item: (-item[1], item[0]))
        return [
            SchemaTable(
                rank=rank,
                name=name,
                score=score,
                summary=_compact_schema_summary(representation),
            )
            for rank, (name, score, representation)
            in enumerate(scored[:FROZEN_FINAL_DEPTH], start=1)
        ]


def project_validator(sql):
    from validation.sql_validator import validate_sql
    return validate_sql(sql)


class SQLServerExecutor:
    """Uses the existing validator, row cap, timeouts, and configured DB login.

    Deployment must provision that login as read-only; no permissions are changed.
    """
    is_demo = False

    def __call__(self, sql):
        from execution.query_executor import execute_query
        result = execute_query(sql, max_rows=100)
        # Existing executor returns ODBC failures rather than raising them.
        detail = str(result.get("execution_error") or "").upper()
        if any(code in detail for code in ("HYT00", "HYT01")):
            raise TimeoutError()
        return result
