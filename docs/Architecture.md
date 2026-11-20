# System Architecture — Engineering Knowledge Intelligence Platform (EKIP)

## 1. Architectural Overview

EKIP is architected around strict separation between **grounded retrieval (RAG)** and **bounded operational agency (MCP)**.
By default, all user queries execute through deterministic, cited retrieval. Agentic execution is strictly reserved for explicit, validated action requests.

```
                                      EKIP Architectural Topology
┌──────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                         USER / CLIENT                                            │
│                        ┌───────────────────────┐   ┌────────────────────────┐                    │
│                        │     Streamlit UI      │   │   External API Client  │                    │
│                        │   (streamlit_app.py)  │   │     (cURL / HTTP)      │                    │
│                        └───────────┬───────────┘   └───────────┬────────────┘                    │
└────────────────────────────────────┼───────────────────────────┼─────────────────────────────────┘
                                     │                           │
┌────────────────────────────────────▼───────────────────────────▼─────────────────────────────────┐
│                                    FastAPI Service Layer                                         │
│                               POST /ask    POST /ingest    GET /health                           │
│                                            (app/api/)                                            │
└────────────────────────────────────────────┬─────────────────────────────────────────────────────┘
                                             │
┌────────────────────────────────────────────▼─────────────────────────────────────────────────────┐
│                                   Orchestration Layer                                            │
│                                (app/services/orchestrator.py)                                    │
│                                                                                                  │
│       ┌──────────────────────────────────────────────────────────────────────────────────┐       │
│       │ 1. Fast-Path Pre-Flight Relevance Check (< 2s)                                   │       │
│       │    - Immediately rejects out-of-scope / non-engineering queries (Zero MCP cost)  │       │
│       └────────────────────────────────────────┬─────────────────────────────────────────┘       │
│                                                │                                                 │
│       ┌────────────────────────────────────────▼─────────────────────────────────────────┐       │
│       │ 2. Intent Classifier (app/chains/classify.py)                                    │       │
│       │    - Routes request to KNOWLEDGE_QUERY or ACTION_REQUEST                         │       │
│       └────────────────────────┬────────────────────────────────┬────────────────────────┘       │
│                                │                                │                                │
│                   KNOWLEDGE_QUERY                               ACTION_REQUEST                   │
│                                │                                │                                │
│       ┌────────────────────────▼─────────────┐   ┌──────────────▼────────────────────────┐       │
│       │ Grounded RAG Chain (LCEL)            │   │ Bounded Agent (app/agents/agent.py)   │       │
│       │ (app/chains/answer.py)               │   │ - Bounded loop (Max 5 iterations)     │       │
│       │ - Multi-sub-database similarity      │   │ - Hard tool allowlist check           │       │
│       │ - Score thresholding (>= 0.35)       │   │ - Dynamic evidence status grading     │       │
│       │ - Strict grounding & cited passages  │   │ - Generates human-review drafts       │       │
│       └────────────────────────┬─────────────┘   └──────────────┬────────────────────────┘       │
│                                │                                │                                │
│                                │                                │ stdio JSON-RPC                 │
│                                │                 ┌──────────────▼────────────────────────┐       │
│                                │                 │ Standalone MCP Server                 │       │
│                                │                 │ (mcp_server/server.py)                │       │
│                                │                 │ Tool: search_runbook                  │       │
│                                │                 └──────────────┬────────────────────────┘       │
│                                │                                │                                │
│       ┌────────────────────────▼────────────────────────────────▼────────────────────────┐       │
│       │ Schema Validation: AnswerResponse (Pydantic v2)                                  │       │
│       │ - answer: str                                                                    │       │
│       │ - citations: List[Citation]                                                      │       │
│       │ - evidence_status: SUFFICIENT | PARTIAL | INSUFFICIENT                           │       │
│       │ - confidence_note: Optional[str]                                                 │       │
│       └──────────────────────────────────────────────────────────────────────────────────┘       │
└──────────────────────────────────────────────────────────────────────────────────────────────────┘
                                             │
┌────────────────────────────────────────────▼─────────────────────────────────────────────────────┐
│                                 Storage & Ingestion Subsystem                                    │
│                                                                                                  │
│   ┌───────────────────────────┐      ┌───────────────────────────┐     ┌──────────────────────┐  │
│   │ Multi-Format Loader       │─────▶│ Heading-Aware Chunker     │────▶│ Vector Indexer       │  │
│   │ 10 Engineering Formats    │      │ Markdown & Document Trees │     │ (app/ingestion/)     │  │
│   └───────────────────────────┘      └───────────────────────────┘     └──────────┬───────────┘  │
│                                                                                   │              │
│   ┌───────────────────────────────────────────────────────────────────────────────▼───────────┐  │
│   │ ChromaDB Vector Store Partitioning (data/chroma_db/)                                      │  │
│   │ ├── manifest.json                        (Archive catalog & chunk metrics)                │  │
│   │ ├── auth_service/chroma.sqlite3          (Sub-database 1)                                 │  │
│   │ └── deployment_runbook/chroma.sqlite3    (Sub-database 2)                                 │  │
│   └───────────────────────────────────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────────────────────────────────────┘
                                             │
┌────────────────────────────────────────────▼─────────────────────────────────────────────────────┐
│                              Observability & Tracing Layer                                       │
│                           LangSmith End-to-End Instrumentation                                   │
│       Traced: Loader ➔ Chunker ➔ Indexer ➔ Retriever ➔ Classifier ➔ RAG ➔ Agent ➔ MCP            │
└──────────────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Core Subsystems

### 2.1 Dual-Engine Execution Architecture
EKIP decouples generation from embeddings, allowing flexible execution setups:
1. **Hosted Engine**: Powered by Google Gemini (`gemini-3.1-flash-lite` for generation and `gemini-embedding-001` for vector representations).
2. **Local Engine**: Powered by local Ollama (`llama3.2:3b` inference and `nomic-embed-text` embeddings). Ideal for modest 4GB VRAM GPUs to eliminate cloud API costs.
3. **Hybrid Mode**: Offload embedding computations locally with zero API cost while leveraging hosted Gemini for fast chat inference.

### 2.2 Storage Partitioning & Archive Manifests
Rather than dumping all vector chunks into a single monolithic index, EKIP isolates data per uploaded `.zip` archive:
- **Raw Files**: Unpacked into `data/uploaded_docs/<archive_slug>/` with Zip Slip security verification.
- **ChromaDB Sub-Databases**: Stored under isolated directories `data/chroma_db/<archive_slug>/`.
- **Manifest Catalog**: `data/chroma_db/manifest.json` preserves the original zip filename, chunk count, document count, and upload timestamp.
- **Dynamic Aggregation**: When querying, `retrieve_chunks()` queries every active sub-database in parallel, merges the candidate chunks, sorts them by cosine relevance, and filters against `RETRIEVAL_MIN_SCORE`.

### 2.3 Bounded Agent & Tool Allowlist Security
When user intent requests operational procedures (e.g., drafting a rollback checklist):
- **Pre-Flight Filter**: Validates whether supporting engineering runbooks exist in vector memory in < 2 seconds. Non-engineering prompts (e.g. food recipes, creative writing) are rejected immediately as `INSUFFICIENT EVIDENCE`, saving compute and API quota.
- **Strict Allowlist**: Tool invocations pass through `app/core/permissions.py`. Models cannot invent or invoke arbitrary tools.
- **Bounded Reasoning Loop**: Hard ceiling of **5 iterations** prevents runaway token consumption or infinite loops.
- **Human-in-the-Loop**: All outputs are flagged as `DRAFTS` requiring engineer review. EKIP possesses zero direct write permissions to production infrastructure.

### 2.4 Model Context Protocol (MCP)
The knowledge search tool is decoupled from the main process:
- **Transport**: Standard JSON-RPC stdio transport.
- **Subprocess Isolation**: The standalone MCP server lives in `mcp_server/server.py` and runs in a separate process spawned on demand by `app/mcp/client.py`.
- **Interoperability**: Any standard MCP client can query EKIP's knowledge corpus using standard MCP specifications.

---

## 3. Security Architecture

| Threat Vector | Mitigation Strategy | Enforcing Component |
|---|---|---|
| **Prompt Injection / Jailbreak** | Non-engineering / off-topic queries are caught in pre-flight and strictly classified as Knowledge Queries, never gaining tool access. | `app/chains/classify.py`, `app/services/orchestrator.py` |
| **Directory Traversal (Zip Slip)** | Archive extraction verifies that resolved target paths strictly reside within the intended upload root. | `app/ingestion/zip_handler.py` |
| **Hallucination** | Mandatory passage extraction; evidence status graded into `SUFFICIENT`, `PARTIAL`, or `INSUFFICIENT`. | `app/chains/answer.py`, `app/api/schemas.py` |
| **Unauthorized Action Execution** | Hardcoded tool allowlist verified prior to model dispatch. Direct production writes strictly forbidden. | `app/core/permissions.py`, `app/agents/agent.py` |
| **Credential Leakage** | All secrets loaded via Pydantic `BaseSettings` from environment variables. Zero raw keys in code. | `app/core/config.py` |

---

## 4. Further Technical References

- **Ingestion & Sub-Databases**: [Ingestion Guide](ingestion_guide.md)
- **Bounded Agent & MCP**: [Agent & MCP Guide](agent_and_mcp_guide.md)
- **Local Engine & Low VRAM**: [Local Engine Setup](local_engine_guide.md)
- **Observability & Benchmarks**: [Evaluation & Observability Guide](eval_and_observability_guide.md)
- **Manual Verification**: [Comprehensive Run & Manual Testing Guide](manual_testing_and_run_guide.md)
