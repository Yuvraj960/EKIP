# Engineering Knowledge Intelligence Platform (EKIP)

[![Python 3.11+](https://img.shields.io/badge/python-3.11%20%7C%203.12-blue.svg)](https://www.python.org/)
[![Tests](https://img.shields.io/badge/pytest-115%20passed%20(100%25)-brightgreen.svg)](tests/unit/)
[![Linter](https://img.shields.io/badge/ruff-passed-brightgreen.svg)](https://github.com/astral-sh/ruff)
[![Type Checker](https://img.shields.io/badge/mypy-passed%20(0%20errors)-brightgreen.svg)](https://mypy-lang.org/)
[![Protocol](https://img.shields.io/badge/MCP-Model%20Context%20Protocol-orange.svg)](https://modelcontextprotocol.io/)
[![Tracing](https://img.shields.io/badge/observability-LangSmith%20Traced-purple.svg)](https://smith.langchain.com/)
[![Engine](https://img.shields.io/badge/engine-Dual--Engine%20(Hosted%20%26%20Local)-blueviolet.svg)](docs/local_engine_guide.md)

> **EKIP** is a production-grade, ground-truth AI assistant designed for software and platform engineering teams. It indexes multi-format technical documentation into partitioned vector sub-databases, delivers grounded answers with verifiable passage-level citations, honestly reports missing evidence, and executes bounded operational actions through the Model Context Protocol (MCP).

---

## Key Highlights & Capabilities

- **100% Citation Grounding**: Every answer is strictly grounded in retrieved engineering documentation, providing the source document name, section heading, and exact passage excerpt.
- **Zero Hallucination Tolerance**: Dynamic evidence grading categorizes confidence into `SUFFICIENT`, `PARTIAL`, or `INSUFFICIENT`. When documentation is absent, EKIP honestly admits missing evidence.
- **Fast-Path Pre-Flight Rejection (< 2s)**: Non-engineering prompts (e.g. recipes, creative writing, jailbreak attempts) are intercepted and rejected in under 2 seconds, saving API quota and eliminating runaway agent loops.
- **Multi-Archive Sub-Database Partitioning**: Uploaded documentation `.zip` archives are organized into dedicated ChromaDB sub-databases with manifest catalog tracking. Add deeper context incrementally or wipe previous data in one click.
- **Multi-Format Document Parsing**: Natively ingests **10 engineering formats**: Markdown (`.md`), PDF (`.pdf`), Word (`.docx`), CSV (`.csv`), TSV (`.tsv`), HTML (`.html`), TXT (`.txt`), JSON (`.json`), YAML (`.yaml`), and reStructuredText (`.rst`).
- **Bounded Operational Agent**: Handles operational requests (e.g. drafting rollback checklists) bounded by a hard **5-iteration ceiling** and strict pre-call tool allowlist checks. All actions produce human-in-the-loop review drafts.
- **Decoupled Model Context Protocol (MCP)**: Tool execution is isolated into a standalone child process over standard JSON-RPC stdio transport.
- **Dual-Engine Execution**: Run with cloud-hosted Google Gemini (`gemini-3.1-flash-lite`), 100% locally with Ollama (`llama3.2:3b` and `nomic-embed-text` on **4GB VRAM GPUs**), or in hybrid configuration.
- **Deep LangSmith Observability**: Custom end-to-end telemetry instrumented across loaders, chunkers, indexers, retrievers, classifiers, LCEL chains, and MCP servers.

---

## System Architecture

```
                                      EKIP Architectural Topology
┌─────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                     CLIENT INTERFACES                                           │
│                 ┌─────────────────────────────┐     ┌────────────────────────────┐              │
│                 │   Streamlit Web Assistant   │     │      FastAPI REST API      │              │
│                 │     (streamlit_app.py)      │     │         (app/api/)         │              │
│                 └──────────────┬──────────────┘     └─────────────┬──────────────┘              │
└────────────────────────────────┼──────────────────────────────────┼─────────────────────────────┘
                                 │                                  │
┌────────────────────────────────▼──────────────────────────────────▼─────────────────────────────┐
│                                     Orchestration Layer                                         │
│                                (app/services/orchestrator.py)                                   │
│                                                                                                 │
│    1. Fast-Path Pre-Flight Check (<2s) ──▶ Short-circuits non-engineering queries               │
│    2. Intent Classifier                ──▶ Routes to KNOWLEDGE_QUERY or ACTION_REQUEST          │
│                                                                                                 │
│                ┌───────────────────────────────────┬───────────────────────────────────┐        │
│                ▼                                   ▼                                   │        │
│   ┌───────────────────────────────┐   ┌───────────────────────────────────────────┐    │        │
│   │   Grounded LCEL RAG Chain     │   │     Bounded Agent (Max 5 iterations)      │    │        │
│   │   - Multi-sub-database search │   │     - Pre-call tool allowlist check       │    │        │
│   │   - Min score filter (>=0.35) │   │     - Dynamic evidence status grading     │    │        │
│   │   - Strict citation assembler │   │     - Generates human-review drafts       │    │        │
│   └───────────────┬───────────────┘   └─────────────────────┬─────────────────────┘    │        │
│                   │                                         │ stdio JSON-RPC           │        │
│                   │                           ┌─────────────▼─────────────┐            │        │
│                   │                           │   Standalone MCP Server   │            │        │
│                   │                           │  (mcp_server/server.py)   │            │        │
│                   │                           └─────────────┬─────────────┘            │        │
│                   ▼                                         ▼                          │        │
│   ┌───────────────────────────────────────────────────────────────────────────────┐    │        │
│   │                      Pydantic v2 AnswerResponse Schema                        │    │        │
│   │        - answer text  - citations list  - evidence_status  - confidence_note  │    │        │
│   └───────────────────────────────────────────────────────────────────────────────┘    │        │
└────────────────────────────────────────────────┬────────────────────────────────────────────────┘
                                                 │
┌────────────────────────────────────────────────▼────────────────────────────────────────────────┐
│                              Partitioned Storage & Vector Store                                 │
│                                                                                                 │
│   data/uploaded_docs/                 data/chroma_db/                                           │
│   ├── auth_service/                   ├── manifest.json            (Corpus catalog)             │
│   └── kubernetes_runbooks/            ├── auth_service/            (Chroma Sub-DB 1)            │
│                                       └── kubernetes_runbooks/     (Chroma Sub-DB 2)            │
└─────────────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## Quickstart in 3 Seconds (Zero-Config Auto-Bootstrapping)

EKIP features **zero-config auto-bootstrapping**. When cloning a fresh repository, you do not need to manually configure environments or install dependencies.

```bash
# 1. Clone the repository
git clone https://github.com/your-org/ekip.git
cd ekip

# 2. Launch the application (everything else is automated!)
ekip start
# On PowerShell: .\ekip start
# On Linux / macOS / Git Bash: ./ekip start
```

### What Happens Automatically:
1. **Dependency Sync**: Checks if `.venv` exists; if missing, automatically runs `uv sync --extra dev`.
2. **Environment Template**: If `.env` is absent, automatically creates it from `.env.example`.
3. **Directory Verification**: Automatically prepares `data/uploaded_docs/` and `data/chroma_db/`.
4. **Instant Launch**: Starts the Streamlit chat assistant on [http://localhost:8501](http://localhost:8501).

> **Note**: For cloud-hosted live Gemini operations, insert your `GOOGLE_API_KEY` into `.env`. If running 100% locally with Ollama, no API key is required!

---

## Core Application Walkthrough

### 1. Zip-First Document Ingestion Landing View
When you launch the app, EKIP presents a focused, single-purpose landing page:
- Drag and drop any `.zip` archive containing your engineering guides, architecture docs, runbooks, or API specs.
- The platform automatically verifies archive integrity, defends against Zip Slip directory traversal, chunks document trees, and embeds vectors into an isolated sub-database.
- Have existing indexed data? Click *"Continue with previously indexed documents"* to jump straight into chat.

### 2. Multi-Archive Sub-Databases & Active Corpus Inspection
- Ingest multiple documentation sets (e.g. `auth_docs.zip`, `k8s_runbooks.zip`) without accidental data collision.
- The sidebar displays the **exact names** of all active sub-databases along with document and chunk statistics.
- When querying, EKIP searches across all active sub-databases, aggregating and ranking the best matching chunks.

### 3. One-Click Database Reset
- Need to wipe stale context? Click **`🗑️ Clear Previous Data (Wipe All Sub-Databases)`** on the upload page or **`🗑️ Clear Database & Reset`** in the sidebar.
- Completely purges previous sub-databases, uploaded raw files, and manifest references in one click.

### 4. Grounded Chat & Verifiable Citations
- Responses display color-coded status badges: `[SUFFICIENT EVIDENCE]`, `[PARTIAL EVIDENCE]`, or `[INSUFFICIENT EVIDENCE]`.
- Click the expandable **`📚 View Sources & Citations`** widget under any answer to inspect the exact document name, section heading, and verbatim passage excerpt.

---

## CLI Reference & Manual (`ekip`)

EKIP comes with a built-in unified command-line dispatcher:

| Command | Description | Example |
|---|---|---|
| `ekip start` | Launch the Streamlit chat web assistant (auto-bootstraps) | `ekip start --port 8501` |
| `ekip api` | Launch FastAPI REST service with Swagger UI at `/docs` | `ekip api --port 8000 --reload` |
| `ekip ingest` | Ingest documentation folder or `.zip` archive | `ekip ingest my_runbooks.zip` |
| `ekip ingest --clear` | Ingest an archive and wipe previous databases first | `ekip ingest docs.zip --clear` |
| `ekip status` | Display active models and list all indexed sub-databases | `ekip status` |
| `ekip reset` | Wipe all Chroma sub-databases, uploaded files, and manifest | `ekip reset --force` |
| `ekip test` | Run isolated unit tests using Pytest | `ekip test` |
| `ekip test --lint` | Run Ruff static code linter and formatting checks | `ekip test --lint` |
| `ekip test --safe` | Run Mypy strict static type safety checks | `ekip test --safe` |
| `ekip test --eval` | Run the 24-case offline ground-truth evaluation suite | `ekip test --eval` |
| `ekip test --full` | Run complete validation (tests + linter + type checks) | `ekip test --full` |
| `ekip eval` | Direct shortcut to run 24-case evaluation benchmark | `ekip eval` |
| `ekip mcp` | Launch standalone Model Context Protocol (MCP) server | `ekip mcp` |
| `ekip help` / `manual` | Display on-the-go terminal command usage manual | `ekip manual` |

*Executable directly via `ekip <command>`, `.\ekip <command>`, or `uv run ekip <command>`.*

---

## Documentation Hub

For detailed operational guides, architecture specifications, and security policies, explore the dedicated documentation modules:

| Documentation Guide | Focus Area |
|---|---|
| 📐 [**System Architecture**](docs/architecture.md) | Architectural topology, component decoupling, data flow, and threat mitigations. |
| 🧪 [**Run & Manual Testing Guide**](docs/manual_testing_and_run_guide.md) | Step-by-step test guide covering every feature and the pre-shipping sign-off checklist. |
| 📦 [**Document Ingestion & Multi-Archive Storage**](docs/ingestion_guide.md) | 10 supported formats, heading-aware chunking, sub-database partitioning, and manifest tracking. |
| 🤖 [**Bounded Agent & Model Context Protocol (MCP)**](docs/agent_and_mcp_guide.md) | 5-iteration loop limits, tool allowlisting, fast-path rejection (<2s), and standalone stdio MCP server. |
| 💻 [**Dual-Engine & Local Ollama (4GB VRAM) Guide**](docs/local_engine_guide.md) | Running 100% locally or in hybrid mode with Ollama (`llama3.2:3b`, `nomic-embed-text`) on modest hardware. |
| 📊 [**Evaluation Benchmark & Observability**](docs/eval_and_observability_guide.md) | LangSmith deep tracing taxonomy, 24-case benchmark runner, and quality metrics. |

---

## Testing & Quality Assurance

With the custom command suite, testing and verifying the codebase is effortless:

```bash
# Run all 115 isolated unit tests
ekip test

# Run Ruff code style checks
ekip test --lint

# Run Mypy static type safety verification
ekip test --safe

# Run the complete CI validation suite
ekip test --full

# Run the 24-case offline evaluation benchmark
ekip eval
```

### Verified Benchmark Performance:
- **Unit Test Coverage**: **115 / 115 tests passing** (`100%`)
- **Linter & Type Checks**: **0 errors** across all 34 source files
- **Overall Benchmark Pass Rate**: **95.8%** (23 / 24 test cases)
- **Answerable Accuracy**: **100.0%** (12 / 12)
- **Safety Rejection**: **100.0%** (4 / 4)
- **Source Citation Match Rate**: **95.8%**

---

## License

Distributed under the MIT License. See `LICENSE` for more information.
