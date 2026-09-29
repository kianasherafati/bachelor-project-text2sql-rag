"""Offline OLD DEV-01/02/03 replay with synthetic SQL/results, never accuracy evidence.

Saved development Top10 context is replayed; no model or database is contacted.
The SQL and row fixtures below only test plumbing, not answers to ERP questions.
"""
from __future__ import annotations

import importlib.metadata
import json
from pathlib import Path
import platform
import sys

if __name__ == '__main__' and __package__ is None:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from evaluation.final_evaluation_contracts import (
    Components, EvaluationCase, Generation, IntegrityError, RunConfig, SchemaContext,
)
from evaluation.final_evaluation_io import canonical, digest, file_sha

ROOT = Path(__file__).resolve().parents[1]
DEV_VERSION = 'OLD-DEV-01-03-SYNTHETIC-EXECUTION-v1'
DEV_INPUT_SHA = '0478f8a84b283e9079ab0345d4bd05e69f31ccc81bb928460bdb0625b5413b67'
DEV_DEFINITIONS_SHA = 'c250593815d53ff73136f5d1eda7c86f12193db268baa3e8c0bbaa1d56daee09'
DATABASE_SHA = digest({'database': 'in-memory-controlled-fixtures-v1'})
GENERATOR_IDENTITY = {
    'model_id': 'DETERMINISTIC-FAKE-NO-MODEL', 'model_revision': 'synthetic-v1',
    'qwen_policy_version': 'NOT-FROZEN-DEV-ONLY',
    'qwen_policy_sha256': digest({'policy': 'deterministic fake; no Qwen policy asserted'}),
}


class ReplayProvider:
    def __init__(self, by_question, identity=None):
        self.by_question = by_question
        self.identity = identity or {'kind': 'OFFLINE_OLD_DEV_TOP10_REPLAY',
                                     'context_sha256': digest({q: [vars(t) for t in ts] for q, ts in by_question.items()})}
        self.calls = []

    def retrieve(self, question):
        self.calls.append(('retrieve', question))
        return tuple(self.by_question[question])

    def rerank(self, question, candidates):
        self.calls.append(('rerank', question))
        return tuple(candidates)


class FakeGenerator:
    is_demo = True
    identity = GENERATOR_IDENTITY

    def __init__(self, outputs):
        self.outputs = outputs
        self.calls = []
        self.prompts = []

    def generate(self, question, context):
        self.calls.append((question, context))
        # Explicit fixture protocol, NOT a proposed final model prompt policy.
        prompt = canonical({'fixture_protocol': 'DEV-ONLY-v1', 'question': question,
                            'schema_context': [{'rank': t.rank, 'fully_qualified_table': t.fully_qualified_table,
                                                'document': t.document} for t in context]})
        self.prompts.append(prompt)
        value = self.outputs[question]
        if isinstance(value, BaseException):
            raise value
        return Generation(value, prompt)


class FixtureCursor:
    """Minimal DB-API fake driven by explicit SQL fixtures, not a SQL interpreter."""
    def __init__(self, connection):
        self.connection = connection
        self._description = None
        self.rows = []
        self.closed = False

    @property
    def description(self):
        if self.closed:
            raise RuntimeError('Cursor is closed')
        return self._description

    def execute(self, sql, *values):
        self.connection.calls.append((sql, values))
        if sql == 'SELECT transaction_isolation_level FROM sys.dm_exec_sessions WHERE session_id=@@SPID':
            self.rows = [(self.connection.isolation_level,)]
            return self
        value = self.connection.results[sql]
        if isinstance(value, BaseException):
            raise value
        names, rows = value
        self._description = [(name, None, None, None, None, 6, None) for name in names]
        self.rows = list(rows)
        return self

    def fetchone(self):
        return self.rows.pop(0) if self.rows else None

    def fetchmany(self, count):
        batch, self.rows = self.rows[:count], self.rows[count:]
        return batch

    def cancel(self):
        pass

    def close(self):
        self.closed = True


class FixtureConnection:
    autocommit = False
    isolation_level = 5
    timeout = 0

    def __init__(self, results):
        self.results = results
        self.calls = []

    def cursor(self):
        return FixtureCursor(self)


def fixture_preflight(connection):
    return {'read_only': True, 'snapshot_isolation': connection.isolation_level == 5,
            'lossless_driver': True, 'memory_supervisor_4gib': True,
            'database_identity_sha256': DATABASE_SHA,
            'transaction_identity_sha256': digest('in-memory-fixture-transaction-v1')}


def development_bundle(run_id):
    from evaluation.final_evaluation_runner import PolicyPairExecutor
    input_path = ROOT / 'evaluation/qwen_preflight_input.jsonl'
    definitions_path = ROOT / 'retrieval/erp_retrieval_benchmark.py'
    # Fixed paths and pinned hashes BEFORE parsing/importing any development data.
    if file_sha(input_path) != DEV_INPUT_SHA or file_sha(definitions_path) != DEV_DEFINITIONS_SHA:
        raise IntegrityError('OLD_DEVELOPMENT_INPUT_HASH_MISMATCH')
    records = [json.loads(line) for line in input_path.read_text(encoding='utf8').splitlines()]
    if [r['case_id'] for r in records] != ['DEV-01', 'DEV-02', 'DEV-03']:
        raise IntegrityError('ONLY_OLD_DEV_01_02_03_ALLOWED')
    from retrieval.erp_retrieval_benchmark import tests as old_development
    from evaluation.qwen_prospective_prompt import validate_record
    cases, contexts, outputs = [], {}, {}
    # Gold and prediction constants are deliberately separate synthetic fixtures.
    gold = ["SELECT N'تهران' AS FixtureValue", 'SELECT 1 AS FixtureValue',
            'SELECT 0 AS FixtureValue WHERE 1=0']
    predictions = ["SELECT N'تهران' AS FixtureValue", 'SELECT 2 AS FixtureValue',
                   'SELECT 0 AS FixtureValue WHERE 1=0']
    results = {gold[0]: (['FixtureValue'], [('تهران',)]), gold[1]: (['FixtureValue'], [(1,)]),
               predictions[1]: (['FixtureValue'], [(2,)]), gold[2]: (['FixtureValue'], [])}
    for i, record in enumerate(records):
        validate_record(record)
        old = old_development[i]
        if old['question'] != record['question']:
            raise IntegrityError('OLD_DEVELOPMENT_QUESTION_MISMATCH')
        cases.append(EvaluationCase(record['case_id'], record['question'], gold[i],
                                    tuple(old['expected_tables']), DEV_VERSION,
                                    source_case_sha256=digest(record)))
        contexts[record['question']] = tuple(SchemaContext(j, t['fully_qualified_table'], t['document'])
                                             for j, t in enumerate(record['tables'], 1))
        outputs[record['question']] = predictions[i]
    provider = ReplayProvider(contexts)
    generator = FakeGenerator(outputs)
    executor = PolicyPairExecutor(FixtureConnection(results), fixture_preflight, is_demo=True)
    config = RunConfig(run_id, DEV_VERSION,
                       digest({'old_input': DEV_INPUT_SHA, 'definitions': DEV_DEFINITIONS_SHA,
                               'synthetic_gold': gold, 'synthetic_predictions': predictions}),
                       provider.identity, generator.identity, DATABASE_SHA,
                       digest({'python': platform.python_version(),
                               'sqlglot': importlib.metadata.version('sqlglot'),
                               'fixture_source': file_sha(__file__)}))
    return tuple(cases), config, Components(provider, generator, executor, {})


if __name__ == '__main__':
    from evaluation.final_evaluation_runner import main
    main()
