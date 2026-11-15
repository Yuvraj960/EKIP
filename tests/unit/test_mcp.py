"""tests.unit.test_mcp — Unit tests for mcp_server and app.mcp.client."""

from unittest.mock import patch

import pytest
from langchain_core.documents import Document

from app.agents.agent import get_agent_tools
from app.mcp.client import get_mcp_tools, invoke_mcp_tool
from mcp_server.server import NO_CONTENT_MSG, search_runbook


def test_mcp_server_search_runbook_empty_query() -> None:
    """Verify MCP server search_runbook returns fallback when query is empty."""
    assert search_runbook("") == NO_CONTENT_MSG
    assert search_runbook("   ") == NO_CONTENT_MSG


def test_mcp_server_search_runbook_with_chunks(sample_chunks: list[Document]) -> None:
    """Verify MCP server search_runbook formats retrieved document chunks."""
    with patch("mcp_server.server.retrieve_chunks", return_value=sample_chunks):
        result = search_runbook("OAuth2 flow")
        assert "[1] SOURCE: auth_guide.md" in result
        assert "The token is validated" in result


def test_invoke_mcp_tool_unauthorized_raises_permission_error() -> None:
    """Verify invoke_mcp_tool blocks unallowlisted tool before invocation."""
    with pytest.raises(PermissionError, match="not in the allowed tool list"):
        invoke_mcp_tool("delete_database", {})


def test_invoke_mcp_tool_allowed_executes() -> None:
    """Verify invoke_mcp_tool executes allowlisted tool over MCP protocol."""
    with patch(
        "app.mcp.client._call_tool_over_stdio_async",
        return_value="[1] SOURCE: auth_guide.md - OAuth2 auth tokens",
    ):
        result = invoke_mcp_tool("search_runbook", {"query": "auth"})
        assert "SOURCE:" in result
        assert "auth" in result.lower()


def test_get_mcp_tools_discovers_allowlisted_tools() -> None:
    """Verify get_mcp_tools returns LangChain tools for permitted tools."""
    tools = get_mcp_tools()
    tool_names = [t.name for t in tools]
    assert "search_runbook" in tool_names


def test_get_agent_tools_combines_mcp_and_local() -> None:
    """Verify agent tools include both MCP tools and local draft tools."""
    tools = get_agent_tools()
    names = [t.name for t in tools]
    assert "search_runbook" in names
    assert "draft_checklist" in names
