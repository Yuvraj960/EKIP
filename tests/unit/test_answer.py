"""tests.unit.test_answer — Unit tests for app.chains.answer."""

from unittest.mock import MagicMock, patch

from langchain_core.documents import Document
from langchain_google_genai import ChatGoogleGenerativeAI

from app.api.schemas import AnswerResponse, Citation, EvidenceStatus
from app.chains.answer import (
    INSUFFICIENT_ANSWER_FALLBACK,
    answer_question,
)


def test_empty_query_returns_insufficient() -> None:
    """Verify that an empty query returns INSUFFICIENT response immediately."""
    res = answer_question("")
    assert res.evidence_status == EvidenceStatus.INSUFFICIENT
    assert res.answer == INSUFFICIENT_ANSWER_FALLBACK
    assert res.citations == []


def test_no_retrieved_chunks_returns_insufficient() -> None:
    """Verify that when no chunks match, INSUFFICIENT is returned without calling LLM."""
    with patch("app.chains.answer.retrieve_chunks", return_value=[]):
        mock_llm = MagicMock(spec=ChatGoogleGenerativeAI)
        res = answer_question("unknown topic query", llm=mock_llm)

        assert res.evidence_status == EvidenceStatus.INSUFFICIENT
        assert res.answer == INSUFFICIENT_ANSWER_FALLBACK
        assert res.citations == []
        mock_llm.with_structured_output.assert_not_called()


def test_answerable_question_returns_citations(sample_chunks: list[Document]) -> None:
    """Verify that retrieved chunks yield an answer with valid citations."""
    mock_llm = MagicMock(spec=ChatGoogleGenerativeAI)
    mock_structured = MagicMock()
    expected_response = AnswerResponse(
        answer="Access tokens are valid for 60 minutes.",
        citations=[
            Citation(
                source="auth_guide.md",
                section="Token Specifications",
                passage_excerpt="Access token validity is 60 minutes.",
            )
        ],
        evidence_status=EvidenceStatus.SUFFICIENT,
        confidence_note="Document explicitly states 60 minutes.",
    )
    mock_structured.return_value = expected_response
    mock_structured.invoke.return_value = expected_response
    mock_llm.with_structured_output.return_value = mock_structured

    with patch("app.chains.answer.retrieve_chunks", return_value=sample_chunks):
        res = answer_question("What is token validity?", llm=mock_llm)

        assert res.evidence_status == EvidenceStatus.SUFFICIENT
        assert "60 minutes" in res.answer
        assert len(res.citations) == 1
        assert res.citations[0].source == "auth_guide.md"


def test_partial_evidence_grading(sample_chunks: list[Document]) -> None:
    """Verify that partial evidence grading returns PARTIAL status."""
    mock_llm = MagicMock(spec=ChatGoogleGenerativeAI)
    mock_structured = MagicMock()
    expected_response = AnswerResponse(
        answer="Token signing is RS256, but key length is unspecified.",
        citations=[
            Citation(
                source="auth_guide.md",
                section="Token Specifications",
                passage_excerpt="Signed JWT using RS256 algorithm.",
            )
        ],
        evidence_status=EvidenceStatus.PARTIAL,
        confidence_note="Key size not mentioned in document.",
    )
    mock_structured.return_value = expected_response
    mock_structured.invoke.return_value = expected_response
    mock_llm.with_structured_output.return_value = mock_structured

    with patch("app.chains.answer.retrieve_chunks", return_value=sample_chunks):
        res = answer_question("What is the private key size?", llm=mock_llm)

        assert res.evidence_status == EvidenceStatus.PARTIAL
        assert len(res.citations) == 1
        assert res.confidence_note is not None
