import unittest

from app.adapters import (
    DemoExecutor,
    DemoGenerator,
    DemoSchemaProvider,
    EXAMPLES,
    FrozenRetrievalResources,
    FrozenRetrievalSchemaProvider,
    _load_representations,
)
from app.pipeline_service import (
    MODE_DEMO,
    MODE_REAL_RETRIEVAL,
    PipelineService,
    create_service,
)


class FakeDenseRetriever:
    def __init__(self):
        self.calls = []

    def retrieve_bge_dense(self, question, top_k):
        self.calls.append((question, top_k))
        return [{"full_name": f"dbo.Table{index:03d}"} for index in range(50)]


class FakeGraphRetriever:
    def __init__(self):
        self.calls = []

    def retrieve_graph_expanded(self, question, top_k):
        self.calls.append((question, top_k))
        return {
            "results": [
                {"full_name": f"dbo.Table{index:03d}"}
                for index in range(25, 75)
            ]
        }


class FakeReranker:
    def __init__(self):
        self.calls = []

    def score(self, question, representation):
        self.calls.append((question, representation))
        score = float(representation.split("SCORE:", 1)[1].splitlines()[0])
        return score, 0.001, 20


def resources():
    representations = {
        f"dbo.Table{index:03d}": (
            f"Identity: fully-qualified table dbo.Table{index:03d}; "
            f"physical table Table{index:03d}; schema dbo\n"
            f"SCORE:{index}\nColumns: ID; Name; Amount"
        )
        for index in range(75)
    }
    return FrozenRetrievalResources(
        dense_retriever=FakeDenseRetriever(),
        graph_retriever=FakeGraphRetriever(),
        reranker=FakeReranker(),
        representations=representations,
    )


def safe_validator(sql):
    return {"valid": True, "cleaned_sql": sql, "errors": []}


class FrozenRetrievalAdapterTests(unittest.TestCase):
    question = "Show a synthetic development report by table."

    def setUp(self):
        self.resources = resources()
        self.provider = FrozenRetrievalSchemaProvider(self.resources)

    def test_real_adapter_contract_and_exact_depth_calls(self):
        candidates = self.provider.retrieve(self.question)
        self.assertEqual(self.resources.dense_retriever.calls, [(self.question, 50)])
        self.assertEqual(self.resources.graph_retriever.calls, [(self.question, 50)])
        self.assertEqual(len(candidates), 75)
        self.assertEqual(len({item.name for item in candidates}), 75)
        self.assertTrue(all("." in item.name for item in candidates))

    def test_actual_frozen_representation_identity_contract(self):
        representations = _load_representations()
        self.assertEqual(len(representations), 2196)
        self.assertTrue(all("." in name for name in representations))
        self.assertTrue(all(text.strip() for text in representations.values()))

    def test_top10_order_identity_scores_and_summary(self):
        final = self.provider.rerank(self.question, self.provider.retrieve(self.question))
        self.assertEqual([item.rank for item in final], list(range(1, 11)))
        self.assertEqual(
            [item.name for item in final],
            [f"dbo.Table{index:03d}" for index in range(74, 64, -1)],
        )
        self.assertEqual([item.score for item in final], [float(index) for index in range(74, 64, -1)])
        self.assertTrue(all("Columns:" in item.summary for item in final))
        self.assertEqual(len({item.name for item in final}), 10)

    def test_frozen_tie_break_is_fully_qualified_name_ascending(self):
        candidates = self.provider.retrieve(self.question)
        for name in ("dbo.Table073", "dbo.Table074"):
            self.resources.representations[name] = self.resources.representations[name].replace(
                f"SCORE:{int(name[-3:])}", "SCORE:100"
            )
        final = self.provider.rerank(self.question, candidates)
        self.assertEqual([item.name for item in final[:2]], ["dbo.Table073", "dbo.Table074"])

    def test_explicit_mode_separation(self):
        with self.assertRaises(ValueError):
            PipelineService(
                self.provider, DemoGenerator(), DemoExecutor(), safe_validator,
                mode=MODE_DEMO,
            )
        with self.assertRaises(ValueError):
            PipelineService(
                DemoSchemaProvider(), DemoGenerator(), DemoExecutor(), safe_validator,
                mode=MODE_REAL_RETRIEVAL,
            )

    def test_mixed_mode_factory_is_lazy(self):
        service = create_service(MODE_REAL_RETRIEVAL)
        self.assertIsInstance(service.schema, FrozenRetrievalSchemaProvider)
        self.assertIsNone(service.schema._injected_resources)
        self.assertEqual(service.mode, MODE_REAL_RETRIEVAL)

    def test_pipeline_response_compatibility(self):
        service = PipelineService(
            self.provider, DemoGenerator(), DemoExecutor(), safe_validator,
            mode=MODE_REAL_RETRIEVAL,
        )
        response = service.run(EXAMPLES["Regional sales"])
        self.assertEqual(response.status, "SUCCESS")
        self.assertEqual(response.mode, MODE_REAL_RETRIEVAL)
        self.assertEqual(len(response.retrieved_tables), 10)
        self.assertEqual(response.retrieved_tables[0].name, "dbo.Table074")
        self.assertEqual(response.rows[0][0], "تهران")


if __name__ == "__main__":
    unittest.main()
