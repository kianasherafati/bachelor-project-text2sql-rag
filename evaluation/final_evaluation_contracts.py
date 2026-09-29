"""Orchestration contracts; no model, benchmark or database loading on import."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

FINAL_VERSION = 'ERP-FINAL-UNSEEN-v1.0'
FINAL_SHA = '8e812121d26259ff7c100a83dce0e07f2f2bc4caf8e68c85614c227672e54fc8'
POLICY_SHA = '151553e510737ff465ece1b1baa6f34f8978adac843f1269f4bfe937b3528410'
POLICY_VERSION = 'EXECUTION-ACCURACY-v1.0'
DEV_LABEL = 'DEVELOPMENT DRY RUN — NOT FINAL EVALUATION'
STAGES = ('RETRIEVAL', 'RERANKING', 'GENERATION', 'OUTPUT_PARSING',
          'VALIDATION', 'GOLD_EXECUTION', 'PREDICTION_EXECUTION', 'RESULT_COMPARISON')
OUTCOMES = ('GENERATION_ERROR', 'VALIDATION_REJECTED', 'EXECUTION_ERROR',
            'RESULT_MISMATCH', 'EXECUTION_CORRECT', 'EVALUATION_BLOCKED', 'EVALUATION_LIMIT')


class IntegrityError(RuntimeError):
    """Stop the run, never turn integrity failures into model scores."""


@dataclass(frozen=True)
class EvaluationCase:
    case_id: str
    question: str
    gold_sql: str
    expected_tables: tuple[str, ...]
    benchmark_version: str
    parameters: dict[str, Any] = field(default_factory=dict)
    source_case_sha256: str | None = None


@dataclass(frozen=True)
class SchemaContext:
    rank: int
    fully_qualified_table: str
    document: str
    score: float | None = None


@dataclass(frozen=True)
class Generation:
    """Prompt must be the exact final rendered text submitted to the model.

    A future frozen adapter owns tokenization/chat templates and any truncation.
    It must return the final rendered text, not the untruncated source messages.
    """
    raw_output: str
    rendered_prompt: str
    status: str = 'SUCCESS'


class Generator(Protocol):
    is_demo: bool
    identity: dict

    def generate(self, question: str, context: tuple[SchemaContext, ...]) -> Generation: ...


class SchemaProvider(Protocol):
    identity: dict

    def retrieve(self, question: str): ...
    def rerank(self, question: str, candidates) -> tuple[SchemaContext, ...]: ...


@dataclass(frozen=True)
class RunConfig:
    run_id: str
    benchmark_version: str
    benchmark_manifest_sha256: str
    retrieval_identity: dict
    generator_identity: dict
    database_identity_sha256: str
    runtime_lock_sha256: str
    mode: str = 'DEV_DRY_RUN'
    evaluation_policy_manifest_sha256: str = POLICY_SHA


@dataclass
class Components:
    provider: SchemaProvider
    generator: Generator
    executor: Any
    schema: dict
