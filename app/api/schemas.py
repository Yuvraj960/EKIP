"""app.api.schemas — Pydantic models for API inputs and outputs.

All data entering and leaving API endpoints and LLM answer generation must
validate against these models. Raw LLM strings are never returned directly.
"""

from enum import StrEnum

from pydantic import BaseModel, Field


class EvidenceStatus(StrEnum):
    """Categorical assessment of evidence sufficiency for an answer."""

    SUFFICIENT = "SUFFICIENT"
    PARTIAL = "PARTIAL"
    INSUFFICIENT = "INSUFFICIENT"


class QueryType(StrEnum):
    """Classification of user query intent."""

    KNOWLEDGE_QUERY = "KNOWLEDGE_QUERY"
    ACTION_REQUEST = "ACTION_REQUEST"


class Citation(BaseModel):
    """Source reference pointing to an indexed document passage.

    Attributes:
        source: Filename of the source document (e.g. 'auth_guide.md').
        section: Nearest heading section in the document.
        passage_excerpt: Direct quote or excerpt from the evidence chunk.
    """

    source: str = Field(description="Filename of the source document.")
    section: str = Field(description="Heading section where the passage appears.")
    passage_excerpt: str = Field(description="Short quote from the evidence passage.")


class AnswerResponse(BaseModel):
    """Structured response returned by the RAG answer pipeline.

    Attributes:
        answer: Synthesized answer grounded solely in retrieved evidence.
        citations: List of citations referencing evidence used.
        evidence_status: Whether evidence was SUFFICIENT, PARTIAL, or INSUFFICIENT.
        confidence_note: Optional explanatory note on evidence quality or caveats.
    """

    answer: str = Field(description="Synthesized answer text.")
    citations: list[Citation] = Field(
        default_factory=list,
        description="List of citations used to formulate the answer.",
    )
    evidence_status: EvidenceStatus = Field(
        description="Assessment of evidence sufficiency.",
    )
    confidence_note: str | None = Field(
        default=None,
        description="Optional note regarding confidence or missing context.",
    )


class QueryClassification(BaseModel):
    """Structured classification result for query routing.

    Attributes:
        query_type: Classified type of the user query.
        reasoning: Brief justification for the classification.
    """

    query_type: QueryType = Field(description="Classified query category.")
    reasoning: str | None = Field(
        default=None,
        description="Brief explanation for the classification.",
    )


class AskRequest(BaseModel):
    """Request payload for asking a question to EKIP.

    Attributes:
        question: User's question string.
        top_k: Number of chunks to retrieve for context.
    """

    question: str = Field(min_length=1, description="Question text.")
    top_k: int = Field(default=5, ge=1, le=20, description="Max chunks to retrieve.")


class HealthResponse(BaseModel):
    """Health check response schema.

    Attributes:
        status: Service health status string.
        version: Application version identifier.
    """

    status: str = Field(default="healthy", description="Service health status.")
    version: str = Field(default="0.1.0", description="Application version.")


class IngestRequest(BaseModel):
    """Request payload to trigger document ingestion.

    Attributes:
        folder_path: Directory path holding engineering documents to index.
    """

    folder_path: str = Field(
        default="data/sample_docs",
        description="Path to documents folder.",
    )


class IngestResponse(BaseModel):
    """Response payload returned after ingestion execution.

    Attributes:
        documents_loaded: Count of parsed document files.
        chunks_indexed: Count of chunk records written to ChromaDB.
        status: Operation outcome status string.
    """

    documents_loaded: int = Field(description="Number of documents loaded.")
    chunks_indexed: int = Field(description="Number of chunks indexed.")
    status: str = Field(default="SUCCESS", description="Execution status.")
