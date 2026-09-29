import unittest

from app.adapters import DemoExecutor, DemoGenerator, DemoSchemaProvider, EXAMPLES
from app.contracts import SchemaTable
from app.pipeline_service import PipelineService, create_service


def safe_validator(sql):
    valid = not sql.lstrip().upper().startswith("DELETE")
    return {"valid": valid, "cleaned_sql": sql,
            "errors": [] if valid else ["Only SELECT queries are allowed."]}


class PipelineServiceTests(unittest.TestCase):
    def service(self):
        return PipelineService(DemoSchemaProvider(), DemoGenerator(), DemoExecutor(), safe_validator)

    def test_success_contract_and_unicode(self):
        response = self.service().run(EXAMPLES["Regional sales"])
        self.assertEqual(response.status, "SUCCESS")
        self.assertEqual(response.columns, ["Region", "SalesTotal"])
        self.assertEqual(response.rows[0][0], "تهران")
        self.assertEqual(response.row_count, 3)
        self.assertEqual(response.execution_status, "success")
        self.assertEqual(set(response.timings), {"retrieval", "reranking", "generation", "validation", "execution", "total"})
        self.assertTrue(all(value >= 0 for value in response.timings.values()))

    def test_insufficient_schema(self):
        response = self.service().run(EXAMPLES["Insufficient schema"])
        self.assertEqual(response.status, "INSUFFICIENT_SCHEMA")
        self.assertEqual(response.generation_status, "INSUFFICIENT_SCHEMA")
        self.assertEqual(response.steps["generation"], "abstained")
        self.assertEqual(response.steps["validation"], "skipped")
        self.assertEqual(response.steps["execution"], "skipped")
        self.assertEqual(response.validation_status, "skipped")
        self.assertEqual(response.execution_status, "skipped")

    def test_validation_rejection_never_executes(self):
        class ExplodingExecutor(DemoExecutor):
            def __call__(self, sql):
                raise AssertionError("executor must not run")
        service = PipelineService(DemoSchemaProvider(), DemoGenerator(), ExplodingExecutor(), safe_validator)
        response = service.run(EXAMPLES["Validation rejected"])
        self.assertEqual(response.status, "VALIDATION_REJECTED")
        self.assertEqual(response.execution_status, "skipped")
        self.assertEqual(response.steps["execution"], "skipped")
        self.assertNotIn("execution", response.timings)

    def test_execution_error_is_sanitized(self):
        response = self.service().run(EXAMPLES["Execution error"])
        self.assertEqual(response.status, "EXECUTION_ERROR")
        self.assertEqual(response.error, "The query could not be completed.")
        self.assertNotIn("Synthetic", response.error)

    def test_empty_result_is_success(self):
        response = self.service().run(EXAMPLES["Empty result"])
        self.assertEqual(response.status, "SUCCESS")
        self.assertEqual(response.rows, [])
        self.assertEqual(response.row_count, 0)

    def test_timeout_and_generation_error(self):
        timeout = self.service().run(EXAMPLES["Timeout"])
        self.assertEqual(timeout.status, "TIMEOUT")
        self.assertEqual(timeout.steps["generation"], "timeout")
        self.assertEqual(timeout.steps["validation"], "skipped")
        self.assertEqual(timeout.steps["execution"], "skipped")
        failure = self.service().run(EXAMPLES["Generation error"])
        self.assertEqual(failure.status, "GENERATION_ERROR")
        self.assertEqual(failure.steps["generation"], "error")
        self.assertEqual(failure.steps["validation"], "skipped")
        self.assertEqual(failure.steps["execution"], "skipped")

    def test_provider_order_is_preserved(self):
        class Provider(DemoSchemaProvider):
            def rerank(self, question, candidates):
                return [SchemaTable(1, "demo.Z"), SchemaTable(2, "demo.A")]
        response = PipelineService(Provider(), DemoGenerator(), DemoExecutor(), safe_validator).run(EXAMPLES["Regional sales"])
        self.assertEqual([item.name for item in response.retrieved_tables], ["demo.Z", "demo.A"])

    def test_demo_and_live_adapters_cannot_be_mixed(self):
        class LiveGenerator(DemoGenerator):
            is_demo = False
        with self.assertRaises(ValueError):
            PipelineService(DemoSchemaProvider(), LiveGenerator(), DemoExecutor(), safe_validator)
        with self.assertRaises(ValueError):
            create_service("live")

    def test_input_bounds(self):
        response = self.service().run(" ")
        self.assertEqual(response.status, "INPUT_ERROR")
        self.assertEqual(response.retrieved_tables, [])


if __name__ == "__main__":
    unittest.main()
