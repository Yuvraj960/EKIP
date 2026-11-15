# docs/architecture.md — System Architecture

> Visual diagrams of the EKIP system architecture.
> Update this file when a new phase changes the system structure.

---

## High-Level System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        EKIP System                              │
│                                                                 │
│  ┌──────────────┐      ┌───────────────────────────────────┐    │
│  │  Streamlit   │      │           FastAPI                 │    │
│  │  Chat UI     │─────▶│  POST /ask   POST /ingest         │    │
│  │  (Phase 4)   │      │  GET  /docs  GET  /health         │    │
│  └──────────────┘      └──────────────┬────────────────────┘    │
│                                       │                         │
│                              ┌────────▼───────────┐             │
│                              │    Orchestrator    │             │
│                              │  (services layer)  │             │
│                              └────┬───────────────┘             │
│                                   │                             │
│                      ┌────────────▼─────────────┐               │
│                      │   Request Classifier     │               │
│                      │  (LangChain LLM call)    │               │
│                      └──────┬──────────┬────────┘               │
│                             │          │                        │
│                    KNOWLEDGE│          │ACTION                  │
│                             │          │                        │
│               ┌─────────────▼───┐  ┌───▼───────────────────┐    │
│               │   RAG Pipeline  │  │   Bounded Agent       │    │
│               │  (LCEL Chain)   │  │   (Phase 5)           │    │
│               │                 │  │                       │    │
│               │ retrieve chunks │  │  Tool: Search         │    │
│               │ format context  │  │  Tool: Draft Checklist│    │
│               │ generate answer │  │                       │    │
│               │ validate output │  │  → MCP Server         │    │
│               └────────┬────────┘  │    (Phase 6)          │    │
│                        │           └──────────┬────────────┘    │
│                        │                      │                 │
│               ┌────────▼──────────────────────▼────────┐        │
│               │         AnswerResponse (Pydantic)      │        │
│               │  answer + citations + evidence_status  │        │
│               └────────────────────┬───────────────────┘        │
│                                    │                            │
│                        ┌───────────▼────────────┐               │
│                        │  LangSmith Tracing     │               │
│                        │  (every model call)    │               │
│                        └────────────────────────┘               │
└─────────────────────────────────────────────────────────────────┘

                    ┌────────────────────────┐
                    │      ChromaDB          │
                    │  (local vector store)  │
                    │                        │
                    │  Collection: ekip_docs │
                    │  - chunk text          │
                    │  - embedding vector    │
                    │  - source metadata     │
                    └────────────────────────┘
                              ▲
                              │ (Phase 2 — ingestion)
                    ┌─────────┴──────────────┐
                    │  Ingestion Pipeline    │
                    │                        │
                    │  load → chunk → embed  │
                    │  → store with metadata │
                    └────────────────────────┘
                              ▲
                    ┌─────────┴──────────────┐
                    │  data/sample_docs/     │
                    │  .md  .pdf  .html      │
                    └────────────────────────┘
```

---

## Module Dependency Map

```
app/core/config.py          ← read by everything
app/core/logging.py         ← read by everything
app/core/errors.py          ← used by API and services
app/core/permissions.py     ← used by agents only

app/ingestion/loaders.py    ← no app dependencies
app/ingestion/chunker.py    ← uses config (CHUNK_SIZE)
app/ingestion/indexer.py    ← uses chunker, config (CHROMA_*)

app/retrieval/retriever.py  ← uses config (CHROMA_*, RETRIEVAL_*)
app/retrieval/context.py    ← uses retriever output

app/chains/classify.py      ← uses config (CHAT_MODEL)
app/chains/answer.py        ← uses retriever, context, config

app/agents/tools.py         ← uses retrieval (search), no external writes
app/agents/agent.py         ← uses tools, permissions, config

app/mcp/client.py           ← connects to mcp_server/server.py

app/services/orchestrator.py ← uses classify, answer, agent
app/api/routes.py           ← uses orchestrator, schemas
app/api/schemas.py          ← Pydantic models only, no dependencies

mcp_server/server.py        ← uses retrieval module
```

---

## RAG Pipeline Detail (Phase 3)

```
Query
  │
  ▼
Retriever (app/retrieval/retriever.py)
  │  - Query ChromaDB with embedding
  │  - Return top-K chunks above min score
  │  - Each chunk has: text, source, title, section, chunk_id
  │
  ▼
Context Assembler (app/retrieval/context.py)
  │  - Format chunks into numbered evidence blocks
  │  - Each block: [SOURCE: filename | SECTION: heading]
  │  - Enforce max context length
  │
  ▼
Answer Chain (app/chains/answer.py — LCEL Runnable)
  │  - System prompt: "Answer only from the evidence below."
  │  - User message: question + formatted evidence
  │  - LLM: Gemini
  │  - Output parser: Pydantic (AnswerResponse)
  │
  ▼
AnswerResponse
  ├── answer: str
  ├── citations: List[Citation]
  │     └── Citation: source, section, passage_excerpt
  ├── evidence_status: "SUFFICIENT" | "INSUFFICIENT" | "PARTIAL"
  └── confidence_note: str (optional)
```

---

## Agent Flow Detail (Phase 5)

```
ACTION_REQUEST query
  │
  ▼
Agent (app/agents/agent.py)
  │  - Receives limited tool list (from allowlist)
  │  - LangChain agent loop
  │
  ├── Tool call attempt
  │     │
  │     ▼
  │   Permission Check (app/core/permissions.py)
  │     - Is this tool in the allowlist? YES → proceed, NO → reject
  │     │
  │     ▼
  │   Tool execution (app/agents/tools.py)
  │     - search_runbook(query) → returns chunks
  │     - draft_checklist(context) → returns markdown draft
  │
  ▼
Agent response (draft / search result)
  │
  ▼
User review (shown in UI before any action is "confirmed")
```

---

## MCP Architecture Detail (Phase 6)

```
┌────────────────────────────────────────┐
│          EKIP Application              │
│                                        │
│  app/agents/agent.py                   │
│        │                               │
│        ▼                               │
│  app/mcp/client.py                     │
│  - Discover tools                      │
│  - Filter via app/core/permissions.py  │
│  - Adapt to LangChain StructuredTool   │
│  - StdioServerParameters               │
└──────────────────┬─────────────────────┘
                   │
                   │ JSON-RPC / MCP Protocol (stdio transport)
                   │
┌──────────────────▼─────────────────────┐
│          Standalone Process            │
│          mcp_server/server.py          │
│                                        │
│  - MCPServer("ekip-knowledge-server")  │
│  - Exposes @mcp.tool() search_runbook  │
│  - Queries ChromaDB & formats context  │
└────────────────────────────────────────┘
```
