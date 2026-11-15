"""tests.unit.test_agent — Unit tests for app.agents.agent and app.agents.tools."""

from unittest.mock import MagicMock, patch

import pytest
from langchain_core.documents import Document
from langchain_core.messages import AIMessage

from app.agents.agent import _execute_tool_call, run_agent
from app.agents.tools import (
    NO_RUNBOOK_FOUND,
    draft_checklist,
    search_runbook,
)


def test_search_runbook_empty_query() -> None:
    """Verify search_runbook returns fallback text when query is empty."""
    assert search_runbook.invoke({"query": ""}) == NO_RUNBOOK_FOUND
    assert search_runbook.invoke({"query": "   "}) == NO_RUNBOOK_FOUND


def test_search_runbook_with_results(sample_chunks: list[Document]) -> None:
    """Verify search_runbook returns formatted context when chunks are found."""
    with patch("app.agents.tools.retrieve_chunks", return_value=sample_chunks):
        result = search_runbook.invoke({"query": "auth tokens"})
        assert "[1] SOURCE: auth_guide.md" in result
        assert "The token is validated" in result


def test_draft_checklist_execution() -> None:
    """Verify draft_checklist invokes model and returns draft markdown."""
    with patch(
        "app.agents.tools._generate_checklist",
        return_value="## Draft Checklist\n- [ ] Step 1",
    ):
        result = draft_checklist.invoke(
            {"task_description": "Rollback", "context": "Sample context"}
        )
        assert "- [ ] Step 1" in result


def test_agent_empty_query() -> None:
    """Verify run_agent returns error message when query is empty."""
    assert run_agent("") == "No action request provided."


def test_execute_tool_call_permission_rejection() -> None:
    """Verify that attempting to call an unlisted tool raises PermissionError."""
    malicious_call = {
        "name": "drop_tables",
        "args": {"table": "users"},
        "id": "bad_call_1",
    }
    with pytest.raises(PermissionError, match="not in the allowed tool list"):
        _execute_tool_call(malicious_call, {})


def test_run_agent_flow() -> None:
    """Verify run_agent invokes model with tools and returns text output."""
    mock_llm = MagicMock()
    mock_bound = MagicMock()

    first_ai_msg = AIMessage(
        content="",
        tool_calls=[
            {
                "name": "search_runbook",
                "args": {"query": "rollback"},
                "id": "call_1",
            }
        ],
    )
    final_ai_msg = AIMessage(content="Here is the drafted checklist:\n- [ ] Step 1")

    mock_bound.invoke.side_effect = [first_ai_msg, final_ai_msg]
    mock_llm.bind_tools.return_value = mock_bound

    with patch("app.agents.tools.retrieve_chunks", return_value=[]):
        output = run_agent("Draft rollback checklist", llm=mock_llm)
        assert "- [ ] Step 1" in output
