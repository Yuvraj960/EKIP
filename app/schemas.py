"""Pydantic models: LLM structured outputs and API contracts."""
from typing import Literal

from pydantic import BaseModel, Field

Category = Literal["document_question", "chitchat", "out_of_scope"]
EvidenceStatus = Literal["supported", "partial", "insufficient"]


# ---- LLM structured outputs -------------------------------------------------
class QuestionType(BaseModel):
    """Classification of the user's message."""

    category: Category = Field(description="Type of the user message")
    reasoning: str = Field(description="One short sentence justifying the category")


class LLMCitation(BaseModel):
    chunk_id: str = Field(description="The chunk id in square brackets, e.g. report-1a2b3c4d-0")
    quote: str = Field(description="Short verbatim snippet (max ~25 words) supporting the answer")


class RAGAnswer(BaseModel):
    answer: str = Field(description="Answer grounded only in the provided context")
    citations: list[LLMCitation] = Field(description="Chunks that support the answer")
    evidence_status: EvidenceStatus = Field(
        description="supported = fully answered by context; partial = only partly; "
        "insufficient = context does not contain the answer"
    )
    confidence: float = Field(description="Confidence between 0.0 and 1.0")


# ---- API contracts ----------------------------------------------------------
class SourceCitation(BaseModel):
    chunk_id: str
    source: str
    title: str
    section: str
    doc_version: str
    quote: str


class ChatTurn(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class ChatRequest(BaseModel):
    question: str = Field(min_length=1)
    history: list[ChatTurn] = []


class ChatResponse(BaseModel):
    answer: str
    question_type: Category
    evidence_status: EvidenceStatus
    confidence: float = Field(ge=0.0, le=1.0)
    citations: list[SourceCitation] = []
