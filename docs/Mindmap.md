# docs/mindmap.md — EKIP Full Project Mindmap

> **Purpose**: This file is the single source of truth for the entire project.
> This should be at the start of every scrum to get full context about project development.
> Update this file whenever a module's role, interface, or dependencies change significantly.


## 1. Project Identity

```
EKIP — Engineering Knowledge Intelligence Platform
├── What it does
│   ├── Answers developer questions from indexed engineering documents
│   ├── Always cites source passages in its answers
│   ├── Admits when evidence is insufficient (no hallucination)
│   └── Runs small bounded actions (search, draft checklist) with approval
│
├── Who uses it
│   ├── Administrator: adds and manages documents
│   └── Developer/User: asks questions, reviews answers and citations
│
└── Design principles
    ├── RAG is the default — agent only for explicit action requests
    ├── All model outputs validated with Pydantic before returning
    ├── Tool calls require explicit permission (allowlist enforced in code)
    ├── Build phase-by-phase — verify before moving forward
    └── Simple over clever — every file has one clear purpose
```

---

## 2. Tech Stack

```
Tech Stack
├── Language: Python 3.11+
├── Package manager: uv (fallback: pip)
│
├── AI / LLM & Embeddings (Dual Engine — DEC-021)
│   ├── Hosted Engine: Google Gemini (gemini-3.1-flash-lite, models/gemini-embedding-001)
│   ├── Local Engine: Ollama / Local Endpoint (llama3.2:3b, nomic-embed-text for 4GB VRAM)
│   ├── Orchestration: LangChain + LCEL (Runnables)
│   └── Tracing + Eval: LangSmith
│
├── Storage
│   ├── Vector store: ChromaDB (local, disk-persisted)
│   └── Document corpus: local filesystem (data/sample_docs/)
│
├── API + UI
│   ├── REST API: FastAPI + Uvicorn
│   └── Chat UI: Streamlit
│
├── Agent + Tools
│   ├── Agent framework: LangChain agent
│   ├── Tool protocol: MCP (Model Context Protocol)
│   └── Tool allowlist: enforced in app/core/permissions.py
│
└── Testing + Quality
    ├── Tests: pytest + pytest-asyncio
    ├── Linter/formatter: ruff
    └── Type checker: mypy
```

---

## 3. Data Flow — How a Query Travels Through the System

```
User question (Streamlit UI)
        │
        ▼
FastAPI route (app/api/routes.py)
        │
        ▼
Orchestrator (app/services/orchestrator.py)
        │
        ▼
Request Classifier (app/chains/classify.py)
        │
   ┌────┴────┐
   │         │
KNOWLEDGE  ACTION
   │         │
   ▼         ▼
RAG Chain  Bounded Agent (app/agents/agent.py)
(answer.py)   │
   │      ┌───┴───┐
   │      │       │
   │   Search   Draft
   │   Tool     Tool
   │      │       │
   │      └───┬───┘
   │          │
   │      (Phase 6: via MCP server)
   │
   ▼
Pydantic validation (AnswerResponse)
        │
        ▼
API response with answer + citations
        │
        ▼
LangSmith trace (every step)
```

---

## 4. Key Invariants

```
Invariants
├── RAG is the default path — agent only for classified ACTION_REQUEST
├── All LLM outputs validated with Pydantic before API return
├── Agent tools checked against allowlist in app/core/permissions.py
├── No raw API keys in source code — all from .env
├── No writes to external systems without explicit user approval
└── Chunk metadata must always include: source, title, section, chunk_id
```

---

## 5. Environment Variables Reference

| Variable | Used in | Purpose |
|----------|---------|---------|
| `GOOGLE_API_KEY` | `app/core/config.py` | Gemini LLM and embedding access |
| `CHAT_MODEL` | `app/chains/` | Which Gemini model for chat |
| `EMBED_MODEL` | `app/ingestion/indexer.py` | Which model for embeddings |
| `LANGSMITH_API_KEY` | Auto-read by LangSmith | Tracing and evaluation |
| `LANGSMITH_PROJECT` | Auto-read by LangSmith | Project grouping in LangSmith UI |
| `CHROMA_PERSIST_DIR` | `app/ingestion/indexer.py` | Where ChromaDB saves data |
| `CHROMA_COLLECTION_NAME` | `app/ingestion/indexer.py` | ChromaDB collection name |
| `RETRIEVAL_TOP_K` | `app/retrieval/retriever.py` | Number of chunks to retrieve |
| `RETRIEVAL_MIN_SCORE` | `app/retrieval/retriever.py` | Min similarity threshold |
| `CHUNK_SIZE` | `app/ingestion/chunker.py` | Characters per chunk |
| `CHUNK_OVERLAP` | `app/ingestion/chunker.py` | Overlap between chunks |
| `API_HOST` | `app/api/routes.py` | FastAPI server host |
| `API_PORT` | `app/api/routes.py` | FastAPI server port |
| `LOG_LEVEL` | `app/core/logging.py` | Logging verbosity |
