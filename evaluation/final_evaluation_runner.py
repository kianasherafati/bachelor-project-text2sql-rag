"""Canonical orchestration. Default CLI mode is offline development only.

No final benchmark module, Qwen runtime or DB connector is imported here.
Final exposure requires a separately frozen release/bootstrap and platform proof.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
from dataclasses import asdict
from datetime import datetime, timezone
import importlib.util
import json
import math
from pathlib import Path
import re
import sys
import time

if __name__ == '__main__':
    # CLI and injected adapters must share one class identity. Otherwise importing
    # the canonical module from the development bundle creates a second executor
    # class and correctly strict type checks would reject the CLI's own bundle.
    sys.modules['evaluation.final_evaluation_runner'] = sys.modules[__name__]

ROOT = Path(__file__).resolve().parents[1]
# Existing frozen policy files use sibling imports; leave their bytes unchanged.
for folder in (ROOT, ROOT / 'evaluation'):
    if str(folder) not in sys.path:
        sys.path.insert(0, str(folder))

import policy_query_executor as frozen_executor
import policy_sql_contract as frozen_sql
from evaluation.final_evaluation_contracts import (
    Components, DEV_LABEL, FINAL_SHA, FINAL_VERSION, Generation, IntegrityError,
    POLICY_SHA, POLICY_VERSION, RunConfig, SchemaContext, STAGES,
)
from evaluation.final_evaluation_io import (
    RunStore, canonical, clean, digest, file_sha, run_lock, safe_text, text_sha,
)

RETRIEVAL_IDENTITY = {
    'architecture': 'BGE-M3 Dense Top50 UNION MiniLM Graph Top50; exact FQ dedup; BGE reranker Top10',
    'dense_model': 'BAAI/bge-m3', 'dense_revision': '5617a9f61b028005a4858fdac845db406aefb181',
    'reranker_model': 'BAAI/bge-reranker-v2-m3', 'reranker_revision': '953dc6f6f85a1b2dbfca4c34a2796e7dde08d41e',
}


def verify_frozen_files(root=ROOT):
    """Byte hashing only for case/Gold/private files: never import or parse them."""
    root = Path(root)
    benchmark_path = root / 'evaluation/final_unseen_freeze_manifest.json'
    policy_path = root / 'evaluation/final_evaluation_policy_manifest.json'
    if file_sha(benchmark_path) != FINAL_SHA:
        raise IntegrityError('BENCHMARK_HASH_MISMATCH')
    if file_sha(policy_path) != POLICY_SHA:
        raise IntegrityError('POLICY_MANIFEST_HASH_MISMATCH')
    benchmark = json.loads(benchmark_path.read_text(encoding='utf8'))
    policy = json.loads(policy_path.read_text(encoding='utf8'))
    items = list(policy['artifacts'])
    for group in ('public_artifacts', 'private_provenance',
                  'retrieval_implementation_and_config', 'schema_and_index_artifacts'):
        items.extend(i for i in benchmark[group] if i['status'] == 'present')
    for item in items:
        path = (root / item['path']).resolve()
        if not path.is_relative_to(root.resolve()) or file_sha(path) != item['sha256']:
            raise IntegrityError('FROZEN_ARTIFACT_HASH_MISMATCH')
    return {'benchmark_manifest_sha256': FINAL_SHA, 'policy_manifest_sha256': POLICY_SHA,
            'verified_artifact_count': len(items)}


def source_hashes():
    files = {
        'runner': 'evaluation/final_evaluation_runner.py',
        'contracts': 'evaluation/final_evaluation_contracts.py',
        'io': 'evaluation/final_evaluation_io.py',
        'dry_run': 'evaluation/run_final_evaluation_dry_run.py',
        'comparator': 'evaluation/policy_result_comparison.py',
        'validator': 'evaluation/policy_sql_contract.py',
        'executor': 'evaluation/policy_query_executor.py',
        'retrieval_adapter': 'app/adapters.py',
    }
    return {name + '_source_sha256': file_sha(ROOT / path) for name, path in files.items()}


def case_identity(case):
    # Private values never leave this boundary; hash binds typed values on resume.
    from policy_result_comparison import value_key
    data = asdict(case)
    data['parameters'] = {key: {'type': type(value).__module__ + '.' + type(value).__qualname__,
                               'value': value_key(value), 'binding_representation': repr(value)}
                          for key, value in case.parameters.items()}
    return digest(data)


def error_info(exc):
    # Only frozen, constant policy codes are safe. Arbitrary exception strings
    # (including ODBC diagnostics, credentials and paths) never enter artifacts.
    codes = {'MALFORMED_OUTPUT', 'PARSE_ERROR', 'EXACTLY_ONE_SELECT_REQUIRED',
             'FORBIDDEN_SQL', 'UNVERIFIED_FUNCTION', 'NONDETERMINISTIC_OR_EXTERNAL_FUNCTION',
             'USER_FUNCTION_REQUIRES_SEPARATE_AUDIT', 'PHYSICAL_TABLE_MUST_BE_LOCAL_TWO_PART_NAME',
             'TABLE_OUTSIDE_ALLOWED_SCHEMA', 'SCHEMA_VALIDATION_FAILED', 'UNBOUND_PARAMETER',
             'NO_RESULT_SET', 'TEMPORAL_PRECISION_NOT_LOSSLESS', 'SNAPSHOT_TRANSACTION_REQUIRED',
             'RESOURCE_LIMIT_INCOMPLETE_RESULT', 'AMBIGUOUS_RESULT_COLUMNS', 'UNSUPPORTED_RESULT_TYPE',
             'NONFINITE_NUMERIC', 'NONFINITE_FLOAT', 'UNSUPPORTED_TIME_OFFSET', 'RESULT_WIDTH_MISMATCH'}
    message = str(exc) if isinstance(exc, frozen_sql.PolicyError) and str(exc) in codes else 'STAGE_FAILED_DETAILS_SUPPRESSED'
    kind = next((name for cls, name in ((MemoryError, 'MemoryError'), (TimeoutError, 'TimeoutError'),
               (frozen_sql.PolicyError, 'PolicyError'), (ValueError, 'ValueError'),
               (RuntimeError, 'RuntimeError')) if isinstance(exc, cls)), 'ComponentError')
    return {'type': kind, 'message_sanitized': message}


class FrozenSchemaProvider:
    """Reuse canonical retrieval/reranking; attach full frozen schema documents.

    UI summaries are intentionally not substituted for model schema context.
    The release bootstrap provides the versioned schema-document mapping.
    """
    identity = RETRIEVAL_IDENTITY

    def __init__(self, documents):
        from app.adapters import FrozenRetrievalSchemaProvider
        self.adapter = FrozenRetrievalSchemaProvider()
        self.documents = documents

    def retrieve(self, question):
        return self.adapter.retrieve(question)

    def rerank(self, question, candidates):
        return tuple(SchemaContext(t.rank, t.name, self.documents[t.name], t.score)
                     for t in self.adapter.rerank(question, candidates))


class _ObservedCursor:
    def __init__(self, cursor, owner):
        self.cursor, self.owner = cursor, owner
        self.stage = None
        self.started = None
        self.error = None
        self.rows = 0

    @property
    def description(self):
        return self.cursor.description

    def execute(self, sql, *values):
        # compare_pair's fixed first query verifies isolation, then Gold/prediction.
        if self.owner.query_index > 0:
            self.stage = ('GOLD_EXECUTION', 'PREDICTION_EXECUTION')[self.owner.query_index - 1]
            self.started = time.perf_counter()
        self.owner.query_index += 1
        try:
            return self.cursor.execute(sql, *values)
        except Exception as exc:
            self.error = exc
            raise

    def fetchone(self):
        return self.cursor.fetchone()

    def fetchmany(self, count):
        try:
            rows = self.cursor.fetchmany(count)
            self.rows += len(rows)
            return rows
        except Exception as exc:
            self.error = exc
            raise

    def cancel(self):
        return self.cursor.cancel()

    def close(self):
        columns = [d[0] for d in (self.description or [])] if self.stage else []
        try:
            return self.cursor.close()
        finally:
            if self.stage:
                self.owner.last_stage = self.stage
                self.owner.observe(self.stage, self.started, self.error, {
                    'row_count': self.rows, 'empty': self.rows == 0,
                    'complete': self.error is None,
                    'columns': columns,
                })


class _ObservedConnection:
    def __init__(self, connection, observe):
        self.connection, self.observe = connection, observe
        self.query_index = 0
        self.last_stage = None

    @property
    def autocommit(self):
        return self.connection.autocommit

    @property
    def timeout(self):
        return self.connection.timeout

    @timeout.setter
    def timeout(self, value):
        self.connection.timeout = value

    def cursor(self):
        return _ObservedCursor(self.connection.cursor(), self)


class PolicyPairExecutor:
    """Execute and compare through frozen compare_pair, without copying its rules.

    Final-mode preflight is a release-hashed callable inspecting the SAME live
    connection and supervisor. No UI executor, row cap, retry or new connection.
    The proof includes transaction identity: process restart cannot silently
    replace the frozen run-wide snapshot transaction.
    """
    def __init__(self, connection, preflight, *, is_demo=False):
        self.connection = connection
        self.preflight = preflight
        self.is_demo = is_demo
        self.last_stage = None
        self._pinned_evidence = None

    def assert_safe(self, expected_identity):
        try:
            evidence = self.preflight(self.connection)
            autocommit = self.connection.autocommit
        except Exception as exc:
            raise IntegrityError('EXECUTION_PREFLIGHT_FAILED') from exc
        required = ('read_only', 'snapshot_isolation', 'lossless_driver', 'memory_supervisor_4gib')
        if (any(evidence.get(k) is not True for k in required)
                or autocommit
                or evidence.get('database_identity_sha256') != expected_identity
                or not re.fullmatch('[a-f0-9]{64}', str(evidence.get('transaction_identity_sha256', '')))):
            raise IntegrityError('UNSAFE_EXECUTION_OR_SNAPSHOT_CHANGED')
        proof = {key: evidence[key] for key in (*required, 'database_identity_sha256', 'transaction_identity_sha256')}
        if self._pinned_evidence is not None and proof != self._pinned_evidence:
            raise IntegrityError('SNAPSHOT_OR_EXECUTION_PROOF_CHANGED')
        self._pinned_evidence = deepcopy(proof)
        return proof

    def compare(self, case, sql, schema, predicted_tables, observe):
        connection = _ObservedConnection(self.connection, observe)
        try:
            return frozen_executor.compare_pair(connection, case.gold_sql, sql,
                                                deepcopy(case.parameters), schema,
                                                case.expected_tables, predicted_tables)
        except frozen_sql.PolicyError as exc:
            if str(exc) == 'SNAPSHOT_TRANSACTION_REQUIRED':
                raise IntegrityError('SNAPSHOT_TRANSACTION_REQUIRED') from exc
            raise
        finally:
            self.last_stage = connection.last_stage


def check_config(config, components, cases):
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,79}', config.run_id):
        raise IntegrityError('INVALID_RUN_ID')
    if not cases or len({c.case_id for c in cases}) != len(cases):
        raise IntegrityError('EMPTY_OR_DUPLICATE_CASES')
    if any(not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,79}', c.case_id)
           or not isinstance(c.question, str) or not c.question.strip() for c in cases):
        raise IntegrityError('INVALID_CASE_CONTRACT')
    if config.evaluation_policy_manifest_sha256 != POLICY_SHA:
        raise IntegrityError('POLICY_HASH_MISMATCH')
    if config.mode not in ('DEV_DRY_RUN', 'FINAL_FROZEN_RUN'):
        raise IntegrityError('INVALID_MODE')
    if any(c.benchmark_version != config.benchmark_version for c in cases):
        raise IntegrityError('MIXED_BENCHMARK')
    if config.mode == 'DEV_DRY_RUN':
        if (config.benchmark_version == FINAL_VERSION or config.benchmark_manifest_sha256 == FINAL_SHA
                or any(c.benchmark_version == FINAL_VERSION for c in cases)
                or components.generator.is_demo is not True or components.executor.is_demo is not True):
            raise IntegrityError('DRY_RUN_FINAL_EXPOSURE_FORBIDDEN')
    else:
        if (config.benchmark_version != FINAL_VERSION or config.benchmark_manifest_sha256 != FINAL_SHA
                or len(cases) != 50 or config.retrieval_identity != RETRIEVAL_IDENTITY
                or not isinstance(components.provider, FrozenSchemaProvider)
                or components.generator.is_demo or components.executor.is_demo):
            raise IntegrityError('FINAL_FROZEN_IDENTITY_MISMATCH')
    if type(components.executor) is not PolicyPairExecutor:
        raise IntegrityError('CANONICAL_READ_ONLY_EXECUTOR_REQUIRED')
    if components.provider.identity != config.retrieval_identity or components.generator.identity != config.generator_identity:
        raise IntegrityError('COMPONENT_IDENTITY_MISMATCH')
    required = {'model_id', 'model_revision', 'qwen_policy_version', 'qwen_policy_sha256'}
    if set(config.generator_identity) != required or not all(config.generator_identity.values()):
        raise IntegrityError('GENERATOR_IDENTITY_INCOMPLETE')
    for value in (config.benchmark_manifest_sha256, config.database_identity_sha256,
                  config.runtime_lock_sha256, config.generator_identity['qwen_policy_sha256']):
        if not re.fullmatch('[a-f0-9]{64}', value):
            raise IntegrityError('INVALID_SHA256')
    if clean(asdict(config)) != asdict(config):
        raise IntegrityError('SENSITIVE_CONFIG_FORBIDDEN')


def run_case(case, config, components):
    started = time.perf_counter()
    record = {
        'case_id': case.case_id, 'case_input_sha256': case_identity(case),
        'source_case_sha256': case.source_case_sha256,
        'question_sha256': text_sha(case.question),
        'benchmark_version': config.benchmark_version,
        'benchmark_manifest_sha256': config.benchmark_manifest_sha256,
        'evaluation_policy_version': POLICY_VERSION,
        'evaluation_policy_manifest_sha256': config.evaluation_policy_manifest_sha256,
        'retrieval_policy_identity': config.retrieval_identity, **config.generator_identity,
        'label': DEV_LABEL if config.mode == 'DEV_DRY_RUN' else 'FINAL FROZEN EVALUATION',
        'stages': {name: {'status': 'SKIPPED', 'elapsed_ms': 0.0, 'error': None} for name in STAGES},
        'retrieved_top10': [], 'prompt_sha256': None, 'generated_raw_output': None,
        'generated_raw_output_sha256': None, 'parsed_sql': None, 'generation_status': 'SKIPPED',
        'validation_message': None, 'gold_result_metadata': {}, 'prediction_result_metadata': {},
        'comparison_reason': None, 'execution_accuracy_outcome': 'GENERATION_ERROR',
        'pipeline_outcome': None, 'error_stage': None, 'error_type': None,
        'error_message_sanitized': None,
        'retrieval_metrics': {'recall_at_10': None, 'full_schema_coverage': None},
    }
    current = 'RETRIEVAL'

    def stage(name, function):
        nonlocal current
        current = name
        before = time.perf_counter()
        try:
            result = function()
            record['stages'][name]['status'] = 'SUCCESS'
            return result
        except Exception as exc:
            record['stages'][name].update(status='ERROR', error=error_info(exc))
            raise
        finally:
            record['stages'][name]['elapsed_ms'] = round((time.perf_counter() - before) * 1000, 3)

    def observe(name, before, error, metadata):
        record['stages'][name] = {'status': 'ERROR' if error else 'SUCCESS',
                                  'elapsed_ms': round((time.perf_counter() - before) * 1000, 3),
                                  'error': error_info(error) if error else None}
        record['gold_result_metadata' if name == 'GOLD_EXECUTION' else 'prediction_result_metadata'] = metadata

    try:
        candidates = stage('RETRIEVAL', lambda: components.provider.retrieve(case.question))
        context = stage('RERANKING', lambda: tuple(components.provider.rerank(case.question, candidates)))
        if (len(context) != 10 or [t.rank for t in context] != list(range(1, 11))
                or len({t.fully_qualified_table for t in context}) != 10
                or any(type(t) is not SchemaContext or not t.document or '.' not in t.fully_qualified_table
                       or (t.score is not None and not math.isfinite(t.score)) for t in context)):
            raise IntegrityError('INVALID_FROZEN_TOP10')
        record['retrieved_top10'] = [{'rank': t.rank, 'fully_qualified_table': t.fully_qualified_table,
                                     'reranker_score': t.score} for t in context]
        # Metrics are calculated AFTER schema input has been independently formed.
        expected = set(case.expected_tables)
        names = {t.fully_qualified_table for t in context}
        record['retrieval_metrics'] = {
            'recall_at_10': len(expected & names) / len(expected) if expected else None,
            'full_schema_coverage': expected <= names,
        }
        generated = stage('GENERATION', lambda: components.generator.generate(case.question, context))
        if type(generated) is not Generation or not isinstance(generated.rendered_prompt, str):
            raise IntegrityError('GENERATOR_CONTRACT_VIOLATION')
        record.update(prompt_sha256=text_sha(generated.rendered_prompt),
                      generated_raw_output=safe_text(generated.raw_output),
                      generated_raw_output_sha256=text_sha(generated.raw_output),
                      generation_status=generated.status)
        if generated.status != 'SUCCESS':
            raise RuntimeError('GENERATION_FAILED')
        parsed = stage('OUTPUT_PARSING', lambda: frozen_sql.extract_output(generated.raw_output))
        if parsed['status'] == 'ABSTAINED':
            record.update(generation_status='INSUFFICIENT_SCHEMA', pipeline_outcome='INSUFFICIENT_SCHEMA')
        else:
            sql = parsed['sql']
            record['parsed_sql'] = safe_text(sql)
            stage('VALIDATION', lambda: frozen_sql.validate_query(sql, components.schema, names))
            record['validation_message'] = 'ACCEPTED'
            components.executor.assert_safe(config.database_identity_sha256)
            total = time.perf_counter()
            try:
                result = stage('RESULT_COMPARISON', lambda: components.executor.compare(
                    case, sql, components.schema, names, observe))
                record.update(execution_accuracy_outcome=result['status'], comparison_reason=result.get('reason'))
            except Exception:
                current = components.executor.last_stage or 'GOLD_EXECUTION'
                # collect()/precision errors happen during the frozen reader after
                # cursor.fetchmany; conservatively invalidate that side's metadata.
                key = 'gold_result_metadata' if current == 'GOLD_EXECUTION' else 'prediction_result_metadata'
                record[key]['complete'] = False
                record['stages']['RESULT_COMPARISON']['status'] = 'SKIPPED'
                raise
            finally:
                # Frozen pair includes its own validation/isolation checks. The
                # residual includes those checks plus actual result comparison.
                pair_ms = (time.perf_counter() - total) * 1000
                execution_ms = sum(record['stages'][s]['elapsed_ms'] for s in ('GOLD_EXECUTION', 'PREDICTION_EXECUTION'))
                record['stages']['RESULT_COMPARISON']['elapsed_ms'] = round(max(0, pair_ms - execution_ms), 3)
    except IntegrityError:
        raise
    except Exception as exc:
        info = error_info(exc)
        record['stages'][current].update(status='ERROR', error=info)
        record.update(error_stage=current, error_type=info['type'], error_message_sanitized=info['message_sanitized'])
        if current == 'GENERATION':
            outcome = 'GENERATION_ERROR'
        elif isinstance(exc, MemoryError) or info['message_sanitized'] == 'RESOURCE_LIMIT_INCOMPLETE_RESULT':
            outcome = 'EVALUATION_LIMIT'
        elif current in ('OUTPUT_PARSING', 'VALIDATION'):
            outcome = 'VALIDATION_REJECTED'
            record['validation_message'] = info['message_sanitized']
        elif current == 'GOLD_EXECUTION' or info['message_sanitized'] in ('TEMPORAL_PRECISION_NOT_LOSSLESS', 'SNAPSHOT_TRANSACTION_REQUIRED'):
            outcome = 'EVALUATION_BLOCKED'
        elif current == 'PREDICTION_EXECUTION':
            outcome = 'EXECUTION_ERROR'
        else:
            outcome = 'GENERATION_ERROR'
        record['execution_accuracy_outcome'] = outcome
        if current == 'GENERATION':
            record['generation_status'] = 'ERROR'
    for prefix, stage_name in [('retrieval', 'RETRIEVAL'), ('reranking', 'RERANKING'),
                               ('generation', 'GENERATION'), ('validation', 'VALIDATION'),
                               ('gold_execution', 'GOLD_EXECUTION'), ('prediction_execution', 'PREDICTION_EXECUTION'),
                               ('comparison', 'RESULT_COMPARISON')]:
        record[prefix + '_elapsed_ms'] = record['stages'][stage_name]['elapsed_ms']
        if prefix != 'generation':
            record[prefix + '_status'] = record['stages'][stage_name]['status']
    record['total_elapsed_ms'] = round((time.perf_counter() - started) * 1000, 3)
    return clean(record)


def run_evaluation(cases, config, components, *, resume=False, output_root=None,
                   final_authorization=None):
    if config.mode == 'FINAL_FROZEN_RUN':
        if final_authorization is not _FINAL_AUTHORIZATION:
            raise IntegrityError('FINAL_RELEASE_GATE_REQUIRED')
        if output_root is not None:
            raise IntegrityError('FINAL_OUTPUT_ROOT_FIXED')
    # Hold immutable private snapshots; component mutation must not mutate the
    # expected identity through an aliased dictionary reference.
    config = deepcopy(config)
    cases = deepcopy(tuple(cases))
    check_config(config, components, cases)
    verify_frozen_files()
    evidence = components.executor.assert_safe(config.database_identity_sha256)
    base = ROOT / 'evaluation' / ('dev_dry_runs' if config.mode == 'DEV_DRY_RUN' else 'final_runs')
    if output_root is not None:
        base = Path(output_root).resolve()
    if config.mode == 'DEV_DRY_RUN' and 'final_runs' in [p.casefold() for p in base.parts]:
        raise IntegrityError('DRY_RUN_FINAL_OUTPUT_FORBIDDEN')
    directory = base / config.run_id
    if directory.is_symlink() or base.is_symlink():
        raise IntegrityError('OUTPUT_SYMLINK_FORBIDDEN')
    directory.mkdir(parents=True, exist_ok=resume)
    manifest = {
        **asdict(config), 'timestamp_utc': datetime.now(timezone.utc).isoformat(),
        'label': DEV_LABEL if config.mode == 'DEV_DRY_RUN' else 'FINAL FROZEN EVALUATION',
        'evaluation_policy_version': POLICY_VERSION, 'case_count': len(cases),
        'case_order': [c.case_id for c in cases], 'case_input_sha256': [case_identity(c) for c in cases],
        'execution_preflight': evidence, **source_hashes(),
        'validation_schema_sha256': digest(components.schema),
        'comparison_timing': 'pair elapsed minus observed SQL reads; includes frozen isolation/validation overhead',
    }
    with run_lock(directory):
        store = RunStore(directory, manifest, resume)
        for case in cases[len(store.records):]:
            if components.executor.assert_safe(config.database_identity_sha256) != evidence:
                raise IntegrityError('SNAPSHOT_OR_EXECUTION_PROOF_CHANGED')
            if components.provider.identity != config.retrieval_identity or components.generator.identity != config.generator_identity:
                raise IntegrityError('COMPONENT_IDENTITY_CHANGED')
            if digest(components.schema) != manifest['validation_schema_sha256']:
                raise IntegrityError('VALIDATION_SCHEMA_CHANGED')
            record = run_case(case, config, components)
            store.append(record)
            if components.executor.assert_safe(config.database_identity_sha256) != evidence:
                raise IntegrityError('SNAPSHOT_OR_EXECUTION_PROOF_CHANGED')
        verify_frozen_files()
        return directory, store.export()


_FINAL_AUTHORIZATION = object()


def final_release(path, expected_sha, run_id, resume):
    """Trusted future release boundary; verify BEFORE importing a case loader.

    Release approval pins bootstrap, runtime lock, Qwen freeze and all code/data
    used by the bootstrap. This is a trusted integration API, not a sandbox for
    arbitrary Python. The bootstrap must perform platform preflight before it
    loads any cases, and return (cases, RunConfig, Components).
    """
    if file_sha(path) != expected_sha:
        raise IntegrityError('RELEASE_HASH_MISMATCH')
    release = json.loads(Path(path).read_text(encoding='utf8'))
    if release.get('final_use_authorized') is not True:
        raise IntegrityError('QWEN_FINAL_FREEZE_REQUIRED')
    verify_frozen_files()
    files = {}
    for name in ('bootstrap', 'runtime_lock', 'qwen_policy'):
        item = release[name]
        source = (ROOT / item['path']).resolve()
        if not source.is_relative_to(ROOT) or file_sha(source) != item['sha256']:
            raise IntegrityError('RELEASE_DEPENDENCY_HASH_MISMATCH')
        files[name] = source
    for rel, expected in release['source_hashes'].items():
        source = (ROOT / rel).resolve()
        if not source.is_relative_to(ROOT) or file_sha(source) != expected:
            raise IntegrityError('RELEASE_SOURCE_HASH_MISMATCH')
    # Must bind orchestration code too, not merely trust a partial caller map.
    if release['runner_sources'] != source_hashes():
        raise IntegrityError('RELEASE_RUNNER_HASH_MISMATCH')
    policy = json.loads(files['qwen_policy'].read_text(encoding='utf8'))
    lock = json.loads(files['runtime_lock'].read_text(encoding='utf8'))
    if policy.get('freeze_status') != 'SUCCESS' or lock.get('final_use_authorized') is not True:
        raise IntegrityError('QWEN_FINAL_FREEZE_REQUIRED')
    import importlib.metadata
    for package, version in lock['packages'].items():
        if importlib.metadata.version(package) != version:
            raise IntegrityError('RUNTIME_LOCK_MISMATCH')
    spec = importlib.util.spec_from_file_location('_approved_final_bootstrap', files['bootstrap'])
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    cases, config, components = module.prepare(run_id=run_id, resume=resume, release=release)
    if (config.mode != 'FINAL_FROZEN_RUN' or config.run_id != run_id
            or config.runtime_lock_sha256 != release['runtime_lock']['sha256']
            or config.generator_identity != release['generator_identity']
            or config.generator_identity['qwen_policy_sha256'] != release['qwen_policy']['sha256']
            or not re.fullmatch('[a-f0-9]{40}', config.generator_identity['model_revision'])
            or digest([case_identity(c) for c in cases]) != release['ordered_case_input_sha256']):
        raise IntegrityError('FINAL_RELEASE_IDENTITY_MISMATCH')
    return run_evaluation(cases, config, components, resume=resume, final_authorization=_FINAL_AUTHORIZATION)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument('--dry-run', action='store_true')
    modes.add_argument('--final-frozen-run', action='store_true')
    parser.add_argument('--run-id', required=True)
    parser.add_argument('--resume', action='store_true')
    parser.add_argument('--release')
    parser.add_argument('--release-sha256')
    args = parser.parse_args()
    if args.final_frozen_run:
        if not args.release or not args.release_sha256:
            parser.error('Final mode requires approved --release and --release-sha256')
        directory, summary = final_release(args.release, args.release_sha256, args.run_id, args.resume)
    else:
        if args.release or args.release_sha256:
            parser.error('Release files cannot be loaded in dry-run mode')
        from evaluation.run_final_evaluation_dry_run import development_bundle
        cases, config, components = development_bundle(args.run_id)
        directory, summary = run_evaluation(cases, config, components, resume=args.resume)
    print(canonical({'artifact_directory': str(directory), 'summary': summary}))


if __name__ == '__main__':
    main()
