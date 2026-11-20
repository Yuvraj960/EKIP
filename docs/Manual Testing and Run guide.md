# EKIP — Comprehensive Run & Manual Testing Guide

## Table of Contents

1. [Environment Setup & Configuration](#1-environment-setup--configuration)
2. [Unified CLI & Quick Launch (`ekip start`)](#2-unified-cli--quick-launch-ekip-start)
3. [Zip Archive Upload & Sub-Database Partitioning](#3-zip-archive-upload--sub-database-partitioning)
4. [One-Click Database Reset Testing](#4-one-click-database-reset-testing)
5. [LangSmith Tracing Setup & Verification](#5-langsmith-tracing-setup--verification)
6. [Core RAG Grounding & Uncertainty Testing](#6-core-rag-grounding--uncertainty-testing)
7. [Bounded Agent & Fast-Path Rejection Testing](#7-bounded-agent--fast-path-rejection-testing)
8. [Model Context Protocol (MCP) Process Isolation Testing](#8-model-context-protocol-mcp-process-isolation-testing)
9. [FastAPI REST Service Manual Testing](#9-fastapi-rest-service-manual-testing)
10. [Automated Evaluation Suite & Quality Sign-Off](#10-automated-evaluation-suite--quality-sign-off)

---

## 1. Environment Setup & Configuration

### Prerequisites
- Python 3.11 or 3.12
- Google Gemini API Key ([Google AI Studio](https://aistudio.google.com/))
- LangSmith API Key ([smith.langchain.com](https://smith.langchain.com/)) *(Optional for observability)*
- `uv` (recommended) or `pip`

### Step 1: Clone and Prepare Virtual Environment
```bash
# Navigate to the project root
cd ekip

# Create and activate virtual environment using uv
uv sync --extra dev
```

### Step 2: Configure Environment Variables
Ensure `.env` exists in the root directory:
```ini
# Primary LLM Credentials
GOOGLE_API_KEY=your_gemini_api_key_here
INFERENCE_MODEL=gemini-3.1-flash-lite
EMBEDDING_MODEL=models/gemini-embedding-001
INFERENCE_ENGINE=HOSTED
EMBEDDING_ENGINE=HOSTED

# LangSmith Observability & Tracing
LANGSMITH_API_KEY=your_langsmith_api_key_here
LANGSMITH_PROJECT=ekip
LANGSMITH_TRACING=true
LANGCHAIN_TRACING_V2=true

# Storage & Retrieval
CHROMA_PERSIST_DIR=./data/chroma_db
UPLOADED_DOCS_DIR=./data/uploaded_docs
RETRIEVAL_TOP_K=5
RETRIEVAL_MIN_SCORE=0.35
```

---

## 2. Unified CLI & Quick Launch (`ekip start`)

EKIP provides a single, custom command to launch any part of the platform.

### Test 2.1: Start the Interactive Web Application
```bash
# Windows CMD or PowerShell
ekip start

# Any platform using uv
uv run ekip start
```
**What to verify**:
- Streamlit launches cleanly on [http://localhost:8501](http://localhost:8501).
- The browser opens automatically or displays the local server link.

### Test 2.2: Launch the REST Backend
```bash
ekip api
```
**What to verify**:
- FastAPI launches on [http://127.0.0.1:8000](http://127.0.0.1:8000).
- Interactive Swagger docs are accessible at `/docs`.

### Test 2.3: Ingest from Terminal
```bash
ekip ingest data/sample_docs/
```
**What to verify**:
- Reports successful chunk and document counts in terminal.

---

## 3. Zip Archive Upload & Sub-Database Partitioning

### Test 3.1: Clean Startup Landing Page
1. Launch `ekip start` in a fresh session.
2. **What to verify**:
   - The user is greeted by a dedicated, single-purpose landing page: **`📦 EKIP — Document Ingestion`**.
   - No chat input or stale messages appear prior to document indexing.

### Test 3.2: Upload & Automatic Partitioned Indexing
1. Prepare a `.zip` file (e.g. `auth_docs.zip` containing Markdown, PDF, Word, or CSV files).
2. Drag and drop `auth_docs.zip` into the file uploader.
3. Click **`🚀 Ingest into Sub-Database`**.
4. **What to verify**:
   - Progress spinner indicates archive extraction, chunking, and embedding.
   - Files are unpacked safely into `data/uploaded_docs/auth_docs/`.
   - Chunks are stored in a partitioned Chroma sub-database: `data/chroma_db/auth_docs/`.
   - The UI displays a success alert and transitions to the live chat interface.

### Test 3.3: Incremental Archive Addition
1. From the chat view sidebar, click **`➕ Add / Manage Archives`**.
2. Upload a second zip (e.g. `kubernetes_runbooks.zip`).
3. Leave `"Clear previous databases..."` unchecked. Click **`🚀 Ingest into Sub-Database`**.
4. **What to verify**:
   - The sidebar under **Active Corpus** now displays **both** archives with their exact filenames and chunk counts!
   - Asking questions about either Auth or Kubernetes yields accurate citations from both corpora.

---

## 4. One-Click Database Reset Testing

### Test 4.1: Reset from Upload Screen
1. On the upload landing page, locate the **`Currently Indexed Sub-Databases`** card.
2. Click **`🗑️ Clear Previous Data (Wipe All Sub-Databases)`**.
3. **What to verify**:
   - A success notification confirms all previous vector databases and references have been wiped.
   - Inspecting `data/chroma_db/` confirms all sub-databases and `manifest.json` have been cleared.

### Test 4.2: Reset from Chat Sidebar
1. While in the chat interface, click **`🗑️ Clear Database & Reset`** in the sidebar.
2. **What to verify**:
   - All past conversation history is purged.
   - The view returns immediately to the clean zip upload screen.

---

## 5. LangSmith Tracing Setup & Verification

1. Ensure `LANGSMITH_TRACING=true` and `LANGSMITH_API_KEY` are present in `.env`.
2. Execute a query in the UI: *"What is the token expiration time?"*
3. Open [smith.langchain.com](https://smith.langchain.com/) -> Select project `ekip`.
4. **What to verify**:
   - A trace appears tagged with `["ekip", "rag", "answer_chain"]`.
   - Latency waterfall breaks down retrieval time, prompt tokens, and completion tokens.
   - Metadata confirms chunk count, active collection, and model name.

---

## 6. Core RAG Grounding & Uncertainty Testing

Execute the following test queries in the Streamlit UI:

| Test Scenario | Sample Query | Expected Evidence Status | Expected Behavior |
|---|---|---|---|
| **Factual Auth** | *"What is the PKCE authorization flow for client apps?"* | `SUFFICIENT` | Answers with step-by-step PKCE exchange citing `authentication_guide.md`. |
| **Canary Rollback** | *"How do we rollback a failed canary release?"* | `SUFFICIENT` | Cites `deployment_runbook.md` with Helm rollback command. |
| **Partial Context** | *"What is the database rollback process and how do we resolve MongoDB replica desync?"* | `PARTIAL` | Explains Alembic rollback, but explicitly flags that MongoDB replica desync is undocumented. |
| **Out-of-Scope** | *"What is the catering budget for the holiday party?"* | `INSUFFICIENT` | Immediately reports missing evidence with 0 hallucinated citations. |
| **Minimum Score** | *"Tell me about random unrelated deployment ideas"* | `INSUFFICIENT` | Chunks falling below score 0.35 are rejected. |

---

## 7. Bounded Agent & Fast-Path Rejection Testing

### Test 7.1: Action Request (Draft Operational Checklist)
Query:
```text
Draft a checklist for conducting a SEV-1 post-mortem investigation.
```
**What to verify**:
1. Intent Classifier routes this as `ACTION_REQUEST`.
2. Agent searches vector memory and drafts a markdown checklist.
3. Callout explicitly warns: *"DRAFT ONLY — Generated checklist must be reviewed by an on-call engineer."*
4. Loop count is strictly bounded to max 5 iterations.

### Test 7.2: Fast-Path Rejection (< 2 seconds)
Query:
```text
Draft me a step-by-step recipe for making mattar paneer.
```
**What to verify**:
1. Fast-path pre-flight check detects 0 supporting engineering runbooks.
2. Query terminates in **< 2 seconds** without invoking the MCP subprocess or agent loops.
3. Evidence status is graded as **`INSUFFICIENT EVIDENCE`**.
4. Output gives a polite refusal explaining EKIP is bounded strictly to engineering procedures.

---

## 8. Model Context Protocol (MCP) Process Isolation Testing

### Test 8.1: Run Standalone MCP Server
```bash
uv run python -m mcp_server.server
```
**What to verify**:
- The server starts and awaits stdio JSON-RPC protocol messages without crashing. Exit with `Ctrl+C`.

### Test 8.2: Automated MCP Unit Test
```bash
uv run pytest tests/unit/test_mcp.py -q
```
**What to verify**:
- Passes with 100% success rate verifying MCP capability negotiation and tool calls over stdio.

---

## 9. FastAPI REST Service Manual Testing

Start the backend: `ekip api`

```bash
# Health Check
curl -X GET "http://127.0.0.1:8000/health"

# Ask Question Endpoint
curl -X POST "http://127.0.0.1:8000/ask" \
     -H "Content-Type: application/json" \
     -d "{\"question\": \"What is the access token expiration time?\", \"top_k\": 5}"
```
**Expected Response**:
- HTTP 200 with JSON matching `AnswerResponse` schema (`answer`, `citations`, `evidence_status: "SUFFICIENT"`).

---

## 10. Automated Evaluation Suite & Quality Sign-Off

Before certifying EKIP for release, run the complete verification suite using custom CLI commands:

```bash
# 1. Run all unit tests (115 tests)
ekip test

# 2. Run Ruff linter and formatting validation
ekip test --lint

# 3. Run Mypy static type safety verification
ekip test --safe

# 4. Run all three quality checks in sequence
ekip test --full

# 5. Run 24-case offline evaluation benchmark
ekip eval
```

### Pre-Shipping Quality Checklist:
- [x] All **115 unit tests pass** without errors.
- [x] Ruff reports **All checks passed!** with 0 warnings.
- [x] Mypy reports **Success: no issues found in 34 source files**.
- [x] Offline evaluation achieves **>= 95% pass rate**.
- [x] Out-of-domain queries are rejected honestly in **< 2 seconds**.
- [x] Sub-databases partition cleanly with zero accidental document stacking.
- [x] Zero-config auto-bootstrapping initializes fresh clones with a single `ekip start` command.
- [x] Streamlit, FastAPI, and CLI launchers work seamlessly.
