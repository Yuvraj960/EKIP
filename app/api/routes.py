"""app.api.routes — FastAPI endpoints for knowledge querying and document ingestion.

Endpoints:
    GET  /health   Health check and version info
    POST /ask      Ask a question answered from indexed engineering documents
    POST /ingest   Trigger ingestion pipeline on a document directory

Usage:
    uvicorn app.api.routes:app --reload --port 8000
"""

from pathlib import Path

from fastapi import FastAPI, HTTPException, status

from app.api.schemas import (
    AnswerResponse,
    AskRequest,
    HealthResponse,
    IngestRequest,
    IngestResponse,
)
from app.ingestion.run_ingest import run_ingestion_pipeline
from app.services.orchestrator import handle_query

APP_TITLE: str = "EKIP API"
APP_VERSION: str = "0.1.0"
HEALTHY_STATUS: str = "healthy"

app = FastAPI(
    title=APP_TITLE,
    version=APP_VERSION,
    description="Engineering Knowledge Intelligence Platform REST API.",
)


@app.get(
    "/health",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Health Check",
)
def health_check() -> HealthResponse:
    """Return system operational status and application version.

    Returns:
        HealthResponse object.
    """
    return HealthResponse(status=HEALTHY_STATUS, version=APP_VERSION)


@app.post(
    "/ask",
    response_model=AnswerResponse,
    status_code=status.HTTP_200_OK,
    summary="Ask Question",
)
def ask(request: AskRequest) -> AnswerResponse:
    """Answer an engineering question using RAG retrieval and citations.

    Args:
        request: AskRequest containing question text and optional top_k.

    Returns:
        AnswerResponse with synthesized answer, citations, and evidence status.
    """
    return handle_query(request.question, top_k=request.top_k)


@app.post(
    "/ingest",
    response_model=IngestResponse,
    status_code=status.HTTP_200_OK,
    summary="Ingest Documents",
)
def ingest_documents(request: IngestRequest) -> IngestResponse:
    """Execute document ingestion and indexing for a directory.

    Args:
        request: IngestRequest specifying folder path.

    Returns:
        IngestResponse with count of loaded documents and indexed chunks.

    Raises:
        HTTPException: If target folder does not exist.
    """
    target_path = Path(request.folder_path)
    if not target_path.is_dir():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Directory not found: '{request.folder_path}'",
        )

    doc_count, chunk_count = run_ingestion_pipeline(target_path)
    return IngestResponse(
        documents_loaded=doc_count,
        chunks_indexed=chunk_count,
        status="SUCCESS",
    )
