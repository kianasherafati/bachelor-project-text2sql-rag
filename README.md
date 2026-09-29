# ERP Text-to-SQL with RAG

Bachelor project for generating Microsoft SQL Server T-SQL queries
from natural-language questions using schema retrieval and a local LLM.

## Current components

- Schema extraction from SQL Server
- SentenceTransformer embeddings
- FAISS schema retrieval
- Qwen2.5-Coder-7B-Instruct
- T-SQL generation

## Demo UI

The Streamlit application is a consumer of one `PipelineService` boundary. Its
default mode is a deterministic, clearly labelled synthetic demo; it does not
run the frozen retrieval/reranking pipeline, Qwen, or SQL Server. The existing
project validator and executor remain available as lazy application adapters for
future live wiring.

From the repository root:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-ui.txt
.\.venv\Scripts\python.exe -m streamlit run ui/streamlit_app.py
```

The demo selector includes success, empty result, insufficient schema,
validation rejection, generation failure, execution failure, and timeout states.
Generated SQL is view-only. Connecting live mode requires explicit compatible
schema retrieval and Qwen generator adapters; the application will never fall
back silently from live mode to demo data.

To run the development mode with the existing frozen candidate retrieval and
reranker, while keeping generation and execution mocked:

```powershell
$env:ERP_APP_MODE = "real_retrieval_mock_generator"
.\.venv\Scripts\python.exe -m streamlit run ui/streamlit_app.py
```

This mode loads the frozen BGE-M3 Dense Top50, MiniLM Graph Top50, and BGE
reranker resources lazily and caches the application service across Streamlit
reruns. It does not enable Qwen or SQL Server execution.

Run the offline application tests without collecting legacy scripts that may
connect to SQL Server:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_pipeline_service -v
```
