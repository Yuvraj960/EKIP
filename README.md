# RAG Documents Chatbot (prototype)

Streamlit UI -> FastAPI -> LCEL RAG pipeline -> Answer + citations

- Chat: `gemini-2.5-flash-lite` · Embeddings: `gemini-embedding-001`
- Vector store: Chroma (persisted in SQLite under `data/chroma/`)
- LangChain: prompts, LCEL runnables, structured output (Pydantic), loaders/splitters, retriever

## Run
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env            # add GOOGLE_API_KEY

uvicorn app.api:app --reload    # terminal 1  (http://localhost:8000/docs)
streamlit run streamlit_app.py  # terminal 2
```

## Pipeline
1. **Ingest**: load (PDF/TXT/MD/DOCX) -> split -> metadata (`source, title, section, doc_version, chunk_id`) -> embed -> Chroma. Re-uploading a file replaces its old chunks.
2. **Classify**: `document_question | chitchat | out_of_scope` (structured output). Non-document messages get a canned reply, no retrieval.
3. **Answer**: similarity retriever (top-k) -> context with chunk ids -> grounded prompt -> `RAGAnswer` (answer, citations, evidence_status, confidence).
4. **Validate**: citations must reference retrieved chunks; uncited answers are downgraded to `insufficient`.

## Next steps
Standalone-question rewriting for follow-ups, metadata filters, reranking, evals, tests.
