"""Offline synthetic orchestration tests. No final cases/models/DB connections."""
from copy import deepcopy
from dataclasses import replace
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from evaluation.final_evaluation_contracts import (
    Components, DEV_LABEL, EvaluationCase, FINAL_SHA, FINAL_VERSION,
    Generation, IntegrityError, RunConfig, SchemaContext, STAGES,
)
from evaluation.final_evaluation_io import RunStore, aggregate, canonical, digest, file_sha, publish, run_lock
from evaluation import final_evaluation_runner as runner
from evaluation.run_final_evaluation_dry_run import (
    DATABASE_SHA, FakeGenerator, FixtureConnection, ReplayProvider, development_bundle,
    fixture_preflight,
)

SQL = 'SELECT ID FROM dbo.Product'
OTHER_SQL = 'SELECT ID FROM dbo.Product WHERE ID=2'
SCHEMA = {'dbo': {'Product': {'ID': 'INT', 'Name': 'NVARCHAR(100)'}}}
CONTEXT = tuple(SchemaContext(i, 'dbo.Product' if i == 1 else f'dbo.Context{i}',
                              'Columns: ID INT; Name NVARCHAR(100)', float(11-i)) for i in range(1, 11))
VERIFY_FROZEN_FILES = runner.verify_frozen_files


def bundle(count=3):
    cases = tuple(EvaluationCase(f'SYN-{i}', f'Exact English question {i}?', SQL,
                                ('dbo.Product',), 'SYNTHETIC-v1') for i in range(count))
    provider = ReplayProvider({c.question: CONTEXT for c in cases})
    generator = FakeGenerator({c.question: SQL for c in cases})
    connection = FixtureConnection({SQL: (['ID'], [(1,), (2,)]), OTHER_SQL: (['ID'], [(2,)])})
    executor = runner.PolicyPairExecutor(connection, fixture_preflight, is_demo=True)
    config = RunConfig('test-run', 'SYNTHETIC-v1', digest('fixture-benchmark'), provider.identity,
                       generator.identity, DATABASE_SHA, digest('fixture-runtime'))
    return cases, config, Components(provider, generator, executor, deepcopy(SCHEMA))


class RunnerTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        # Hash the actual frozen bytes separately in the integrity check. Unit
        # tests avoid repeatedly streaming all large immutable index files.
        self.verify = patch.object(runner, 'verify_frozen_files', return_value={}).start()
        self.addCleanup(patch.stopall)
        self.cases, self.config, self.parts = bundle()

    def run_fixture(self, *, resume=False, cases=None, config=None):
        path, summary = runner.run_evaluation(self.cases if cases is None else cases,
                                             config or self.config, self.parts,
                                             output_root=self.root, resume=resume)
        records = [json.loads(line) for line in (path / 'per_case_results.jsonl').read_text(encoding='utf8').splitlines()]
        return path, summary, records

    def test_deterministic_order_preserves_input_not_id_sort(self):
        order = (self.cases[2], self.cases[0], self.cases[1])
        _, _, rows = self.run_fixture(cases=order)
        self.assertEqual([r['case_id'] for r in rows], [c.case_id for c in order])
        self.assertEqual([q for q, _ in self.parts.generator.calls], [c.question for c in order])

    def test_separate_stage_status_and_timing(self):
        _, _, rows = self.run_fixture()
        for row in rows:
            self.assertEqual(set(row['stages']), set(STAGES))
            for stage in row['stages'].values():
                self.assertEqual(stage['status'], 'SUCCESS')
                self.assertGreaterEqual(stage['elapsed_ms'], 0)
                self.assertIsNone(stage['error'])
            self.assertEqual(row['gold_result_metadata']['row_count'], 2)
            self.assertTrue(row['prediction_result_metadata']['complete'])

    def test_expected_tables_and_gold_never_reach_retrieval_or_generator(self):
        cases = (replace(self.cases[0], gold_sql="SELECT 71 AS SecretGold",
                         expected_tables=('private.ExpectedOnly',), parameters={'SecretParameter': 'private-value'}),)
        self.parts.executor.connection.results['SELECT 71 AS SecretGold'] = (['SecretGold'], [(71,)])
        _, _, rows = self.run_fixture(cases=cases)
        self.assertEqual(self.parts.provider.calls, [('retrieve', cases[0].question), ('rerank', cases[0].question)])
        self.assertEqual(self.parts.generator.calls, [(cases[0].question, CONTEXT)])
        text = self.parts.generator.prompts[0]
        for secret in ('SecretGold', 'private.ExpectedOnly', 'SecretParameter', 'private-value',
                       'SYNTHETIC-v1', 'SYN-0', 'recall_at_10', 'difficulty', 'domain'):
            self.assertNotIn(secret, text)
        self.assertEqual(rows[0]['retrieval_metrics']['recall_at_10'], 0)
        self.assertFalse(rows[0]['retrieval_metrics']['full_schema_coverage'])

    def test_exact_prompt_hash(self):
        _, _, rows = self.run_fixture()
        self.assertEqual(rows[0]['prompt_sha256'], runner.text_sha(self.parts.generator.prompts[0]))

    def test_validation_rejection_skips_both_executions(self):
        self.parts.generator.outputs[self.cases[0].question] = 'SELECT ID INTO dbo.Copy FROM dbo.Product'
        _, _, rows = self.run_fixture(cases=self.cases[:1])
        self.assertEqual(rows[0]['execution_accuracy_outcome'], 'VALIDATION_REJECTED')
        self.assertEqual(rows[0]['validation_message'], 'FORBIDDEN_SQL')
        self.assertEqual(rows[0]['prediction_execution_status'], 'SKIPPED')
        self.assertEqual(self.parts.executor.connection.calls, [])

    def test_malformed_output_rejected_without_execution(self):
        self.parts.generator.outputs[self.cases[0].question] = 'Here is SQL: SELECT 1'
        _, _, rows = self.run_fixture(cases=self.cases[:1])
        self.assertEqual(rows[0]['error_stage'], 'OUTPUT_PARSING')
        self.assertEqual(rows[0]['execution_accuracy_outcome'], 'VALIDATION_REJECTED')
        self.assertEqual(self.parts.executor.connection.calls, [])

    def test_generation_error_continues(self):
        self.parts.generator.outputs[self.cases[0].question] = RuntimeError('PWD=super-secret;UID=private')
        _, summary, rows = self.run_fixture()
        self.assertEqual(rows[0]['execution_accuracy_outcome'], 'GENERATION_ERROR')
        self.assertEqual(rows[1]['execution_accuracy_outcome'], 'EXECUTION_CORRECT')
        self.assertEqual(summary['completed_count'], 3)
        self.assertEqual(rows[0]['error_stage'], 'GENERATION')

    def test_retrieval_and_reranking_failures_are_separate_and_continue(self):
        retrieve = self.parts.provider.retrieve
        rerank = self.parts.provider.rerank
        def fail_retrieve(question):
            if question == self.cases[0].question:
                raise RuntimeError('fixture retrieval failure')
            return retrieve(question)
        def fail_rerank(question, candidates):
            if question == self.cases[1].question:
                raise RuntimeError('fixture reranking failure')
            return rerank(question, candidates)
        with patch.object(self.parts.provider, 'retrieve', side_effect=fail_retrieve), \
                patch.object(self.parts.provider, 'rerank', side_effect=fail_rerank):
            _, _, rows = self.run_fixture()
        self.assertEqual([r['error_stage'] for r in rows], ['RETRIEVAL', 'RERANKING', None])
        self.assertEqual(rows[2]['execution_accuracy_outcome'], 'EXECUTION_CORRECT')

    def test_generation_oom_is_frozen_generation_error(self):
        self.parts.generator.outputs[self.cases[0].question] = MemoryError()
        _, _, rows = self.run_fixture(cases=self.cases[:1])
        self.assertEqual(rows[0]['execution_accuracy_outcome'], 'GENERATION_ERROR')

    def test_prediction_execution_error_continues(self):
        self.parts.generator.outputs[self.cases[0].question] = OTHER_SQL
        self.parts.executor.connection.results[OTHER_SQL] = RuntimeError('Driver=secret;PWD=secret')
        _, _, rows = self.run_fixture()
        self.assertEqual(rows[0]['execution_accuracy_outcome'], 'EXECUTION_ERROR')
        self.assertEqual(rows[0]['gold_execution_status'], 'SUCCESS')
        self.assertEqual(rows[0]['prediction_execution_status'], 'ERROR')
        self.assertEqual(rows[1]['execution_accuracy_outcome'], 'EXECUTION_CORRECT')

    def test_result_mismatch_and_correct(self):
        self.parts.generator.outputs[self.cases[0].question] = OTHER_SQL
        _, summary, rows = self.run_fixture()
        self.assertEqual(rows[0]['execution_accuracy_outcome'], 'RESULT_MISMATCH')
        self.assertEqual(rows[1]['execution_accuracy_outcome'], 'EXECUTION_CORRECT')
        self.assertEqual(summary['execution_accuracy'], 2/3)

    def test_empty_gold_delegates_frozen_structural_safeguard(self):
        self.parts.executor.connection.results[SQL] = (['ID'], [])
        self.parts.executor.connection.results[OTHER_SQL] = (['ID'], [])
        self.parts.generator.outputs[self.cases[0].question] = OTHER_SQL
        original = runner.frozen_executor.compare_pair
        with patch.object(runner.frozen_executor, 'compare_pair', wraps=original) as delegated:
            _, summary, rows = self.run_fixture()
        self.assertEqual(delegated.call_count, 3)
        self.assertEqual(rows[0]['comparison_reason'], 'EMPTY_STRUCTURE_UNVERIFIED')
        self.assertEqual(rows[0]['execution_accuracy_outcome'], 'RESULT_MISMATCH')
        self.assertEqual(rows[1]['execution_accuracy_outcome'], 'EXECUTION_CORRECT')
        self.assertEqual(summary['gold_strata']['empty'], {'count': 3, 'correct': 2})

    def test_manifest_and_case_serialization(self):
        path, _, rows = self.run_fixture()
        manifest = json.loads((path / 'run_manifest.json').read_text(encoding='utf8'))
        self.assertEqual(manifest['case_count'], 3)
        for field in ('runtime_lock_sha256', 'database_identity_sha256', 'benchmark_manifest_sha256',
                      'evaluation_policy_manifest_sha256', 'runner_source_sha256',
                      'comparator_source_sha256', 'validator_source_sha256', 'executor_source_sha256'):
            self.assertRegex(manifest[field], '^[a-f0-9]{64}$')
        self.assertEqual(manifest['label'], DEV_LABEL)
        self.assertEqual(json.loads(canonical(rows)), rows)

    def test_unicode_persian_output_serialization_without_result_rows(self):
        sql = "SELECT N'تهران' AS City"
        self.parts.generator.outputs[self.cases[0].question] = sql
        self.parts.executor.connection.results[sql] = (['City'], [('تهران',)])
        path, _, rows = self.run_fixture(cases=(replace(self.cases[0], gold_sql=sql),))
        self.assertIn('تهران', (path / 'per_case_results.jsonl').read_text(encoding='utf8'))
        self.assertEqual(rows[0]['execution_accuracy_outcome'], 'EXECUTION_CORRECT')
        self.assertNotIn('rows', rows[0]['gold_result_metadata'])

    def test_completed_cases_immutable_and_resume_skips_generation(self):
        path, summary, _ = self.run_fixture()
        before = {p.name: p.read_bytes() for p in (path / 'cases').glob('*')}
        generator_calls = len(self.parts.generator.calls)
        _, resumed, _ = self.run_fixture(resume=True)
        self.assertEqual(summary, resumed)
        self.assertEqual(len(self.parts.generator.calls), generator_calls)
        self.assertEqual(before, {p.name: p.read_bytes() for p in (path / 'cases').glob('*')})
        with self.assertRaises(FileExistsError):
            publish(path / 'cases/00000.json', {'overwrite': True})

    def test_rerun_requires_new_run_id(self):
        self.run_fixture()
        with self.assertRaises(FileExistsError):
            self.run_fixture()
        _, summary, _ = self.run_fixture(config=replace(self.config, run_id='new-run'))
        self.assertEqual(summary['completed_count'], 3)

    def test_crash_resume_only_uncompleted_cases(self):
        generate = self.parts.generator.generate
        def interrupt(question, context):
            if question == self.cases[1].question:
                raise KeyboardInterrupt()
            return generate(question, context)
        with patch.object(self.parts.generator, 'generate', side_effect=interrupt):
            with self.assertRaises(KeyboardInterrupt):
                self.run_fixture()
        first = (self.root / 'test-run/cases/00000.json').read_bytes()
        _, summary, _ = self.run_fixture(resume=True)
        self.assertEqual([q for q, _ in self.parts.generator.calls], [c.question for c in self.cases])
        self.assertEqual(first, (self.root / 'test-run/cases/00000.json').read_bytes())
        self.assertEqual(summary['completed_count'], 3)

    def test_changed_input_and_order_rejected_before_generation(self):
        self.run_fixture()
        count = len(self.parts.generator.calls)
        for cases in (tuple(reversed(self.cases)), (replace(self.cases[0], gold_sql=OTHER_SQL), *self.cases[1:]),
                      (replace(self.cases[0], parameters={'ID': 9}), *self.cases[1:])):
            with self.subTest(cases=cases[0].case_id):
                with self.assertRaises(IntegrityError):
                    self.run_fixture(cases=cases, resume=True)
        self.assertEqual(len(self.parts.generator.calls), count)

    def test_corrupted_case_checksum_rejected(self):
        path, _, _ = self.run_fixture()
        case_path = path / 'cases/00000.json'
        entry = json.loads(case_path.read_text())
        entry['record']['execution_accuracy_outcome'] = 'RESULT_MISMATCH'
        case_path.write_text(canonical(entry))
        with self.assertRaises(IntegrityError):
            self.run_fixture(resume=True)

    def test_deleted_completed_tail_rejected_by_receipt(self):
        path, _, _ = self.run_fixture()
        (path / 'cases/00002.json').unlink()
        with self.assertRaises(IntegrityError):
            self.run_fixture(resume=True)

    def test_corrupt_manifest_and_aggregate_rejected(self):
        path, _, _ = self.run_fixture()
        (path / 'summary.json').write_text('{}')
        with self.assertRaisesRegex(IntegrityError, 'CORRUPT_AGGREGATE'):
            self.run_fixture(resume=True)
        (path / 'run_manifest.json').write_text('{}')
        with self.assertRaises(IntegrityError):
            self.run_fixture(resume=True)

    def test_interrupted_publish_receipt_blocks_regeneration(self):
        from evaluation import final_evaluation_io as io
        original = io.publish
        def fail_case(path, value):
            if Path(path).parent.name == 'cases':
                raise OSError('Simulated process interruption')
            return original(path, value)
        with patch.object(io, 'publish', side_effect=fail_case):
            with self.assertRaises(OSError):
                self.run_fixture()
        count = len(self.parts.generator.calls)
        with self.assertRaisesRegex(IntegrityError, 'INCOMPLETE_OR_DELETED_COMPLETION'):
            self.run_fixture(resume=True)
        self.assertEqual(len(self.parts.generator.calls), count)

    def test_dry_run_final_benchmark_guard(self):
        for config, cases in ((replace(self.config, benchmark_version=FINAL_VERSION), self.cases),
                              (replace(self.config, benchmark_manifest_sha256=FINAL_SHA), self.cases),
                              (self.config, (replace(self.cases[0], benchmark_version=FINAL_VERSION),))):
            with self.assertRaises(IntegrityError):
                self.run_fixture(config=config, cases=cases)
        self.assertFalse(self.parts.generator.calls)

    def test_dry_run_blocks_real_generator_and_executor(self):
        self.parts.generator.is_demo = False
        with self.assertRaises(IntegrityError):
            self.run_fixture()
        self.parts.generator.is_demo = True
        self.parts.executor.is_demo = False
        with self.assertRaises(IntegrityError):
            self.run_fixture()
        self.assertFalse(self.parts.generator.calls)

    def test_dry_run_final_output_path_blocked(self):
        with self.assertRaises(IntegrityError):
            runner.run_evaluation(self.cases, self.config, self.parts, output_root=self.root / 'final_runs')
        self.assertFalse((self.root / 'final_runs').exists())

    def test_final_mode_requires_release_and_no_loader_on_dry_cli(self):
        with self.assertRaises(IntegrityError):
            self.run_fixture(config=replace(self.config, mode='FINAL_FROZEN_RUN'))
        result = subprocess.run([sys.executable, '-B', '-m', 'evaluation.final_evaluation_runner',
                                 '--dry-run', '--run-id', 'never', '--release', 'DO-NOT-LOAD.json'],
                                cwd=runner.ROOT, capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('cannot be loaded in dry-run', result.stderr)

    def test_final_release_requires_authorization_before_bootstrap(self):
        release = self.root / 'release.json'
        release.write_text(canonical({'final_use_authorized': False}))
        with self.assertRaisesRegex(IntegrityError, 'QWEN_FINAL_FREEZE_REQUIRED'):
            runner.final_release(release, file_sha(release), 'never', False)

    def test_final_gate_blocks_lazy_case_loader(self):
        def loader():
            self.fail('Case loader must not be iterated without final authorization')
            yield None
        with self.assertRaisesRegex(IntegrityError, 'FINAL_RELEASE_GATE_REQUIRED'):
            runner.run_evaluation(loader(), replace(self.config, mode='FINAL_FROZEN_RUN'), self.parts)

    def test_real_hash_verifier_rejects_wrong_benchmark_and_policy(self):
        with patch.object(runner, 'file_sha', return_value='0'*64):
            with self.assertRaisesRegex(IntegrityError, 'BENCHMARK_HASH_MISMATCH'):
                VERIFY_FROZEN_FILES()
        with patch.object(runner, 'file_sha', side_effect=[FINAL_SHA, '0'*64]):
            with self.assertRaisesRegex(IntegrityError, 'POLICY_MANIFEST_HASH_MISMATCH'):
                VERIFY_FROZEN_FILES()

    def test_frozen_hash_mismatch_stops_before_generation(self):
        self.verify.side_effect = IntegrityError('BENCHMARK_HASH_MISMATCH')
        with self.assertRaises(IntegrityError):
            self.run_fixture()
        self.assertFalse(self.parts.generator.calls)

    def test_policy_and_component_identity_mismatch_blocked(self):
        with self.assertRaises(IntegrityError):
            self.run_fixture(config=replace(self.config, evaluation_policy_manifest_sha256='0'*64))
        self.parts.provider.identity = {'wrong': 'revision'}
        with self.assertRaises(IntegrityError):
            self.run_fixture()

    def test_snapshot_change_stops_entire_run(self):
        calls = 0
        def changed(connection):
            nonlocal calls
            calls += 1
            proof = fixture_preflight(connection)
            if calls > 2:
                proof['database_identity_sha256'] = digest('different-db')
            return proof
        self.parts.executor.preflight = changed
        with self.assertRaises(IntegrityError):
            self.run_fixture()
        self.assertLessEqual(len(self.parts.generator.calls), 1)

    def test_unsafe_executor_never_runs(self):
        self.parts.executor.connection.autocommit = True
        with self.assertRaises(IntegrityError):
            self.run_fixture()
        self.assertFalse(self.parts.generator.calls)

    def test_transaction_change_after_generation_stops_before_sql(self):
        generate = self.parts.generator.generate
        def mutate(question, context):
            result = generate(question, context)
            self.parts.executor.preflight = lambda connection: dict(fixture_preflight(connection),
                                                    transaction_identity_sha256=digest('new transaction'))
            return result
        with patch.object(self.parts.generator, 'generate', side_effect=mutate):
            with self.assertRaisesRegex(IntegrityError, 'SNAPSHOT_OR_EXECUTION_PROOF_CHANGED'):
                self.run_fixture()
        self.assertFalse(self.parts.executor.connection.calls)

    def test_changed_validation_schema_rejected_on_resume(self):
        self.run_fixture()
        self.parts.schema['dbo']['Product']['NewColumn'] = 'INT'
        with self.assertRaisesRegex(IntegrityError, 'RESUME_MANIFEST_MISMATCH'):
            self.run_fixture(resume=True)

    def test_same_parameter_values_bound_both_sides(self):
        sql = 'SELECT ID FROM dbo.Product WHERE ID=@ID'
        self.parts.generator.outputs[self.cases[0].question] = sql
        self.parts.executor.connection.results[sql.replace('@ID', '?')] = (['ID'], [(7,)])
        case = replace(self.cases[0], gold_sql=sql, parameters={'ID': 7})
        self.run_fixture(cases=(case,))
        queries = self.parts.executor.connection.calls[1:]
        self.assertEqual(queries, [(sql.replace('@ID', '?'), (7,))] * 2)

    def test_parameter_binding_type_is_part_of_case_identity(self):
        from decimal import Decimal
        self.assertNotEqual(runner.case_identity(replace(self.cases[0], parameters={'ID': 1})),
                            runner.case_identity(replace(self.cases[0], parameters={'ID': Decimal('1.0')})))

    def test_no_credentials_or_driver_exception_text_in_artifacts(self):
        secret = 'Password=topsecret;UID=admin;Server=private-host'
        self.parts.generator.outputs[self.cases[0].question] = RuntimeError(secret)
        self.parts.generator.outputs[self.cases[1].question] = 'SELECT 1 AS x -- ' + secret
        path, _, _ = self.run_fixture()
        for artifact in path.rglob('*'):
            if artifact.is_file():
                data = artifact.read_text(encoding='utf8')
                self.assertNotIn('topsecret', data)
                self.assertNotIn('private-host', data)
                self.assertNotIn('UID=admin', data)

    def test_deterministic_summary_no_timestamp_or_timing_effect(self):
        _, summary, rows = self.run_fixture()
        altered = deepcopy(rows)
        for row in altered:
            row['total_elapsed_ms'] = 987654321
        self.assertEqual(summary, aggregate(altered, 3, DEV_LABEL))
        self.assertEqual(summary, aggregate(list(reversed(rows)), 3, DEV_LABEL))

    def test_insufficient_schema_preserves_pipeline_outcome_and_frozen_score(self):
        self.parts.generator.outputs[self.cases[0].question] = 'INSUFFICIENT_SCHEMA'
        _, summary, rows = self.run_fixture()
        self.assertEqual(rows[0]['pipeline_outcome'], 'INSUFFICIENT_SCHEMA')
        self.assertEqual(rows[0]['execution_accuracy_outcome'], 'GENERATION_ERROR')
        self.assertEqual(rows[0]['prediction_execution_status'], 'SKIPPED')
        self.assertEqual(summary['insufficient_schema_count'], 1)

    def test_gold_failure_blocks_publication_not_model_error(self):
        cases = (replace(self.cases[0], gold_sql=OTHER_SQL), *self.cases[1:])
        self.parts.executor.connection.results[OTHER_SQL] = RuntimeError('Gold fixture failed')
        _, summary, rows = self.run_fixture(cases=cases)
        self.assertEqual(rows[0]['execution_accuracy_outcome'], 'EVALUATION_BLOCKED')
        self.assertEqual(summary['publication_status'], 'BLOCKED')
        self.assertIsNone(summary['execution_accuracy'])

    def test_complete_results_not_ui_100_row_limit(self):
        self.parts.executor.connection.results[SQL] = (['ID'], [(i,) for i in range(700)])
        _, _, rows = self.run_fixture(cases=self.cases[:1])
        self.assertEqual(rows[0]['gold_result_metadata']['row_count'], 700)
        self.assertEqual(rows[0]['prediction_result_metadata']['row_count'], 700)
        self.assertEqual(rows[0]['execution_accuracy_outcome'], 'EXECUTION_CORRECT')

    def test_resource_limit_is_censored_not_prefix_correct(self):
        import policy_result_comparison
        with patch.object(policy_result_comparison, 'MAX_ROWS', 1):
            _, summary, rows = self.run_fixture()
        self.assertEqual(rows[0]['execution_accuracy_outcome'], 'EVALUATION_LIMIT')
        self.assertFalse(rows[0]['gold_result_metadata']['complete'])
        self.assertEqual(summary['resource_censored_count'], 3)
        self.assertEqual(summary['execution_accuracy'], 0)

    def test_duplicate_cases_rejected(self):
        with self.assertRaises(IntegrityError):
            self.run_fixture(cases=(self.cases[0], self.cases[0]))

    def test_lock_blocks_concurrent_writer(self):
        self.root.mkdir(exist_ok=True)
        with run_lock(self.root):
            with self.assertRaises(IntegrityError):
                with run_lock(self.root):
                    self.fail('Concurrent writer entered')

    def test_old_development_bundle_only(self):
        cases, config, components = development_bundle('dev-fixture-contract')
        self.assertEqual([c.case_id for c in cases], ['DEV-01', 'DEV-02', 'DEV-03'])
        self.assertTrue(components.generator.is_demo)
        self.assertTrue(components.executor.is_demo)
        self.assertEqual(config.mode, 'DEV_DRY_RUN')
        self.assertNotEqual(config.benchmark_manifest_sha256, FINAL_SHA)
        self.assertFalse(components.generator.calls)

    def test_cli_module_and_adapter_share_canonical_class_identity(self):
        code = '''import runpy, sys
sys.argv = ['final_evaluation_runner', '--help']
try:
    runpy.run_module('evaluation.final_evaluation_runner', run_name='__main__', alter_sys=True)
except SystemExit as exc:
    assert exc.code == 0
from evaluation import final_evaluation_runner as runner
from evaluation.run_final_evaluation_dry_run import development_bundle
cases, config, components = development_bundle('cli-contract-only')
runner.check_config(config, components, cases)
assert type(components.executor) is runner.PolicyPairExecutor
assert not components.generator.calls
'''
        result = subprocess.run([sys.executable, '-B', '-c', code], cwd=runner.ROOT,
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == '__main__':
    unittest.main()
