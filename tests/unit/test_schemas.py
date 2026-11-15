"""tests.unit.test_schemas — Unit tests for app.api.schemas."""

import pytest
from pydantic import ValidationError

from app.api.schemas import (
    AnswerResponse,
    AskRequest,
    Citation,
    EvidenceStatus,
    QueryClassification,
    QueryType,
)


def test_citation_model_valid() -> None:
    """Verify that Citation validates and holds correct fields."""
    citation = Citation(
        source="auth_guide.md",
        section="OAuth2 Flow",
        passage_excerpt="Access token validity is 60 minutes.",
    )
    assert citation.source == "auth_guide.md"
    assert citation.section == "OAuth2 Flow"
    assert "60 minutes" in citation.passage_excerpt


def test_answer_response_valid() -> None:
    """Verify that AnswerResponse validates with full citation payload."""
    citation = Citation(
        source="deployment_runbook.md",
        section="Rollback",
        passage_excerpt="Run ekip-deploy rollback",
    )
    response = AnswerResponse(
        answer="The rollback command is ekip-deploy rollback.",
        citations=[citation],
        evidence_status=EvidenceStatus.SUFFICIENT,
        confidence_note="Direct match found.",
    )
    assert response.evidence_status == EvidenceStatus.SUFFICIENT
    assert len(response.citations) == 1
    assert response.confidence_note == "Direct match found."


def test_answer_response_invalid_status() -> None:
    """Verify validation error when evidence status is invalid string."""
    with pytest.raises(ValidationError):
        AnswerResponse(
            answer="Some answer",
            citations=[],
            evidence_status="UNKNOWN_STATUS",  # type: ignore[arg-type]
        )


def test_query_classification_model() -> None:
    """Verify QueryClassification validates enum and optional reasoning."""
    qc = QueryClassification(
        query_type=QueryType.KNOWLEDGE_QUERY,
        reasoning="User is asking for factual documentation.",
    )
    assert qc.query_type == QueryType.KNOWLEDGE_QUERY
    assert qc.reasoning is not None


def test_ask_request_validation() -> None:
    """Verify AskRequest validates positive top_k and non-empty question."""
    req = AskRequest(question="How to authenticate?", top_k=3)
    assert req.question == "How to authenticate?"
    assert req.top_k == 3

    with pytest.raises(ValidationError):
        AskRequest(question="", top_k=3)

    with pytest.raises(ValidationError):
        AskRequest(question="Valid question", top_k=0)
