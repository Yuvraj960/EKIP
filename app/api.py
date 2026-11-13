"""FastAPI layer between the chat UI and the RAG pipeline."""
from pathlib import Path

from fastapi import FastAPI, HTTPException, UploadFile

from app.config import get_settings
from app.ingestion import SUPPORTED, ingest_file, list_documents
from app.rag import get_pipeline, to_history
from app.schemas import ChatRequest, ChatResponse

app = FastAPI(title="RAG Documents Chatbot")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/documents")
def documents():
    return list_documents()


@app.post("/ingest")
def ingest(files: list[UploadFile]):
    upload_dir = get_settings().upload_dir
    upload_dir.mkdir(parents=True, exist_ok=True)
    indexed, errors = [], []
    for f in files:
        name = Path(f.filename).name
        if Path(name).suffix.lower() not in SUPPORTED:
            errors.append({"file": name, "error": "Unsupported file type"})
            continue
        dest = upload_dir / name
        dest.write_bytes(f.file.read())
        try:
            indexed.append(ingest_file(dest))
        except Exception as e:  # report per-file, keep going
            errors.append({"file": name, "error": str(e)})
    return {"indexed": indexed, "errors": errors}


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    try:
        return get_pipeline().invoke(
            {"question": req.question, "history": to_history(req.history)}
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Pipeline error: {e}")
