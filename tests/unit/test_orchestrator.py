"""tests.unit.test_orchestrator — Unit tests for app.services.orchestrator."""

from unittest.mock import MagicMock, patch

from app.api.schemas import AnswerResponse, Citation, EvidenceStatus, QueryType
from app.services.orchestrator import handle_query


def test_handle_query_routes_knowledge_query() -> None:
    """Verify KNOWLEDGE_QUERY calls answer_question with correct query."""
    dummy_response = AnswerResponse(
        answer="Auth documentation is in auth_guide.md",
        citations=[],
        evidence_status=EvidenceStatus.SUFFICIENT,
    )
    with (
        patch("app.services.orchestrator.classify_query", return_value=QueryType.KNOWLEDGE_QUERY),
        patch("app.services.orchestrator.answer_question", return_value=dummy_response) as mock_ans,
    ):
        result = handle_query("Where is auth documented?", top_k=3)
        assert result.answer == "Auth documentation is in auth_guide.md"
        mock_ans.assert_called_once_with("Where is auth documented?", top_k=3)


def test_handle_query_routes_action_request_with_supporting_docs() -> None:
    """Verify ACTION_REQUEST with supporting docs routes to run_agent and sets SUFFICIENT."""
    mock_agent_output = "- [ ] Step 1: Verify canary health\n- [ ] Step 2: Rollback revision"
    dummy_chunk = MagicMock()
    dummy_citation = Citation(
        source="deployment_runbook.md", section="Canary", passage_excerpt="Rollback step"
    )
    with (
        patch("app.services.orchestrator.classify_query", return_value=QueryType.ACTION_REQUEST),
        patch("app.services.orchestrator.retrieve_chunks", return_value=[dummy_chunk]),
        patch("app.services.orchestrator.extract_citations", return_value=[dummy_citation]),
        patch("app.services.orchestrator.run_agent", return_value=mock_agent_output) as mock_agent,
    ):
        result = handle_query("Create a deployment checklist", top_k=5)
        assert result.evidence_status == EvidenceStatus.SUFFICIENT
        assert "Step 1: Verify canary health" in result.answer
        assert len(result.citations) == 1
        assert result.confidence_note is not None
        mock_agent.assert_called_once_with("Create a deployment checklist")


def test_handle_query_action_request_no_supporting_docs_short_circuits() -> None:
    """Verify ACTION_REQUEST without supporting chunks short-circuits to INSUFFICIENT."""
    with (
        patch("app.services.orchestrator.classify_query", return_value=QueryType.ACTION_REQUEST),
        patch("app.services.orchestrator.retrieve_chunks", return_value=[]),
        patch("app.services.orchestrator.run_agent") as mock_agent,
    ):
        result = handle_query("Draft step by step guide for mattar paneer recipe")
        assert result.evidence_status == EvidenceStatus.INSUFFICIENT
        assert "do not have enough relevant engineering runbook documentation" in result.answer
        assert result.citations == []
        mock_agent.assert_not_called()


def test_handle_query_action_request_agent_refusal_marks_insufficient() -> None:
    """Verify agent refusal or missing runbook response is graded INSUFFICIENT."""
    refusal_output = "I apologize, but I do not have access to recipe databases in my runbooks."
    dummy_chunk = MagicMock()
    with (
        patch("app.services.orchestrator.classify_query", return_value=QueryType.ACTION_REQUEST),
        patch("app.services.orchestrator.retrieve_chunks", return_value=[dummy_chunk]),
        patch("app.services.orchestrator.run_agent", return_value=refusal_output),
    ):
        result = handle_query("Draft cooking guide")
        assert result.evidence_status == EvidenceStatus.INSUFFICIENT
        assert result.citations == []
        assert "I apologize" in result.answer
