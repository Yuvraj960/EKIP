"""tests.unit.test_classify — Unit tests for app.chains.classify."""

from unittest.mock import MagicMock

from langchain_google_genai import ChatGoogleGenerativeAI

from app.api.schemas import QueryClassification, QueryType
from app.chains.classify import classify_query


def test_classify_empty_query_defaults_to_knowledge() -> None:
    """Verify empty query returns KNOWLEDGE_QUERY without calling model."""
    assert classify_query("") == QueryType.KNOWLEDGE_QUERY
    assert classify_query("   ") == QueryType.KNOWLEDGE_QUERY


def test_classify_action_request() -> None:
    """Verify that an action request returns ACTION_REQUEST."""
    mock_llm = MagicMock(spec=ChatGoogleGenerativeAI)
    mock_structured = MagicMock()
    expected = QueryClassification(
        query_type=QueryType.ACTION_REQUEST,
        reasoning="User requested drafting a rollback checklist.",
    )
    mock_structured.return_value = expected
    mock_structured.invoke.return_value = expected
    mock_llm.with_structured_output.return_value = mock_structured

    result = classify_query("Draft a rollback checklist", llm=mock_llm)
    assert result == QueryType.ACTION_REQUEST


def test_classify_knowledge_query() -> None:
    """Verify that a factual question returns KNOWLEDGE_QUERY."""
    mock_llm = MagicMock(spec=ChatGoogleGenerativeAI)
    mock_structured = MagicMock()
    expected = QueryClassification(
        query_type=QueryType.KNOWLEDGE_QUERY,
        reasoning="User is asking for token expiration time.",
    )
    mock_structured.return_value = expected
    mock_structured.invoke.return_value = expected
    mock_llm.with_structured_output.return_value = mock_structured

    result = classify_query("How long is the access token valid?", llm=mock_llm)
    assert result == QueryType.KNOWLEDGE_QUERY
