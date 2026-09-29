from dataclasses import dataclass, field
from typing import Any, Protocol, Sequence

STEPS = ("retrieval", "reranking", "generation", "validation", "execution")


@dataclass(frozen=True)
class SchemaTable:
    rank: int
    name: str
    summary: str = ""
    score: float | None = None


class SchemaProvider(Protocol):
    is_demo: bool

    def retrieve(self, question: str) -> Sequence[SchemaTable]: ...

    def rerank(self, question: str, candidates: Sequence[SchemaTable]) -> Sequence[SchemaTable]: ...


class Generator(Protocol):
    is_demo: bool

    def generate(self, question: str, tables: Sequence[SchemaTable]) -> str:
        """Return T-SQL (optionally fenced) or exactly INSUFFICIENT_SCHEMA.

        Runtime adapters own transport deadlines and raise TimeoutError on timeout.
        No Colab or evaluation artifact dependency is permitted here.
        """
        ...


@dataclass
class PipelineResponse:
    question: str
    mode: str
    status: str = "WAITING"
    retrieved_tables: list[SchemaTable] = field(default_factory=list)
    generated_sql: str = ""
    generation_status: str = "waiting"
    validation_status: str = "waiting"
    validation_message: str = ""
    execution_status: str = "waiting"
    columns: list[str] = field(default_factory=list)
    rows: list[list[Any]] = field(default_factory=list)
    timings: dict[str, float] = field(default_factory=dict)
    steps: dict[str, str] = field(default_factory=lambda: dict.fromkeys(STEPS, "waiting"))
    error: str | None = None

    @property
    def row_count(self) -> int:
        return len(self.rows)
