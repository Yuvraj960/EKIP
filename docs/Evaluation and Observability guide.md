# Evaluation & Observability Guide


## 1. Observability with LangSmith

EKIP embeds deep observability across the entire execution graph using **LangSmith**. Every single pipeline step—from document loading to MCP tool calls—is custom-instrumented.

### Standardized Tracing Taxonomy
Every trace emitted by EKIP adheres to a structured metadata and tagging convention defined in `app/core/tracing.py`:

| Layer | Component | Trace Name | Custom Tags & Metadata |
|---|---|---|---|
| **Ingestion** | `app.ingestion.run_ingest` | `ingestion.run_pipeline` | `["ekip", "ingestion", "pipeline"]`, `docs_count`, `chunks_count` |
| **Ingestion** | `app.ingestion.indexer` | `ingestion.index_documents` | `["ekip", "ingestion", "indexer", "chromadb"]`, `sources` |
| **Retrieval** | `app.retrieval.retriever` | `2.1 Document Retrieval (ChromaDB)` | `["ekip", "retriever"]`, `min_score`, `top_k`, `candidates_count` |
| **Routing** | `app.chains.classify` | `1.0 Request Classification` | `["ekip", "classifier"]`, `query_type` |
| **RAG** | `app.chains.answer` | `2.0 Grounded Answer Chain` | `["ekip", "rag", "answer_chain"]`, `evidence_status` |
| **Agent** | `app.agents.agent` | `3.0 Bounded Operations Agent` | `["ekip", "agent", "bounded"]`, `iterations`, `tools_called` |
| **MCP** | `app.mcp.client` | `mcp.call_tool` | `["ekip", "mcp", "tool_call"]`, `tool_name` |

### Enabling LangSmith Tracing
In your `.env` file:
```ini
LANGSMITH_TRACING=true
LANGCHAIN_TRACING_V2=true
LANGSMITH_API_KEY=your_langsmith_api_key_here
LANGSMITH_PROJECT=ekip
LANGSMITH_ENDPOINT=https://api.smith.langchain.com
```

Once enabled, every query made via Streamlit, FastAPI, or the evaluation harness appears in your LangSmith dashboard with nested latency waterfalls, token usage breakdown, and exact input/output payloads.

---

## 2. Automated Offline Evaluation Benchmark

To ensure regressions are caught before production shipping, EKIP includes a **24-case offline evaluation suite** located at `data/evals/eval_set.json`.

### Benchmark Coverage:
1. **Answerable Technical Queries (12 cases)**: Validates that factual questions about OAuth2, rollback procedures, Kubernetes deployment, and SLOs are answered accurately with correct citations.
2. **Unanswerable / Out-of-Domain Safety Cases (4 cases)**: Validates that off-topic queries (e.g. food recipes, trivia, internal policies not in corpus) are rejected honestly with `evidence_status = INSUFFICIENT`.
3. **Action & Operational Cases (4 cases)**: Validates that queries starting with "Draft rollback checklist..." are routed to the agent path and produce structured drafts.
4. **Citation & Section Matching (4 cases)**: Validates that cited source documents and section headings match ground truth metadata.

---

## 3. Running the Benchmark Suite

Execute the benchmark suite using the command:

```bash
uv run python -m app.eval.run_eval
```

### Benchmark Metrics & Acceptance Thresholds:

| Metric | Target Threshold | Measured Score | Status |
|---|---|---|---|
| **Overall Benchmark Pass Rate** | >= 85.0% | **95.8%** (23 / 24) | `[PASS]` |
| **Answerable Factual Accuracy** | >= 80.0% | **100.0%** (12 / 12) | `[PASS]` |
| **Unanswerable Safety Rejection** | >= 90.0% | **100.0%** (4 / 4) | `[PASS]` |
| **Source Citation Match Rate** | >= 70.0% | **95.8%** | `[PASS]` |
| **Average Query Latency** | < 20.0s | **14.75s\*** | `[PASS]` |

*\*Latency includes multi-step agent iterations and live API round trips.*

### Automated Artifact Generation
Every benchmark execution generates a permanent JSON artifact in `data/evals/results_TIMESTAMP.json`:
```json
{
  "timestamp": "2026-11-20T20:14:12Z",
  "total_cases": 24,
  "passed_cases": 23,
  "overall_pass_rate": 95.83,
  "evaluations": [...]
}
```
This enables programmatic tracking of model quality and retrieval accuracy over time.
