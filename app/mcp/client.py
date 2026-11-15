"""app.mcp.client — Model Context Protocol (MCP) client.

Connects to the EKIP MCP server (mcp_server/server.py), discovers available
tools, and adapts allowlisted tools into LangChain BaseTool objects.

Usage:
    from app.mcp.client import get_mcp_tools
    tools = get_mcp_tools()
"""

import asyncio
import concurrent.futures
import sys
from collections.abc import Coroutine
from typing import Any, TypeVar

from langchain_core.tools import BaseTool, StructuredTool
from langsmith import traceable
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from app.core.permissions import assert_tool_allowed, check_tool_allowed
from app.core.tracing import (
    META_MODULE,
    META_TOOL_NAME,
    RUN_TYPE_TOOL,
    TAG_EKIP,
    TAG_MCP,
    TAG_TOOL,
    add_trace_metadata,
    add_trace_tags,
)
from mcp_server.server import mcp as local_mcp_server

T = TypeVar("T")


def _run_sync(coro: Coroutine[Any, Any, T]) -> T:
    """Safely execute an asynchronous coroutine from synchronous caller.

    Args:
        coro: Asynchronous coroutine to execute.

    Returns:
        Result value of the coroutine.
    """
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            return pool.submit(asyncio.run, coro).result()
    return asyncio.run(coro)


def get_mcp_server_params() -> StdioServerParameters:
    """Return configured parameters to launch MCP server as a subprocess.

    Returns:
        StdioServerParameters pointing to the mcp_server module.
    """
    return StdioServerParameters(
        command=sys.executable,
        args=["-m", "mcp_server.server"],
    )


async def _call_tool_over_stdio_async(
    tool_name: str,
    arguments: dict[str, Any],
) -> str:
    """Invoke an MCP tool over stdio transport.

    Args:
        tool_name: Name of the tool to invoke.
        arguments: Arguments dictionary for the tool.

    Returns:
        Extracted text content from the MCP response.
    """
    server_params = get_mcp_server_params()
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            call_res = await session.call_tool(tool_name, arguments)
            if call_res.content and hasattr(call_res.content[0], "text"):
                return str(call_res.content[0].text)
            return str(call_res)


@traceable(
    name="mcp.invoke_tool",
    run_type=RUN_TYPE_TOOL,
    tags=[TAG_EKIP, TAG_MCP, TAG_TOOL],
    metadata={META_MODULE: "app.mcp.client"},
)
def invoke_mcp_tool(tool_name: str, arguments: dict[str, Any]) -> str:
    """Invoke an MCP tool with permission check and fallback support.

    Args:
        tool_name: Allowlisted tool name.
        arguments: Keyword arguments for the tool call.

    Returns:
        Tool output text.

    Raises:
        PermissionError: If tool_name is not registered in ALLOWED_TOOLS.
    """
    add_trace_tags([f"mcp_tool:{tool_name}"])
    add_trace_metadata({META_TOOL_NAME: tool_name, "arguments": arguments})
    assert_tool_allowed(tool_name)
    try:
        return _run_sync(_call_tool_over_stdio_async(tool_name, arguments))
    except Exception:
        # Fallback to local in-process MCPServer instance
        res = _run_sync(local_mcp_server.call_tool(tool_name, arguments))
        if hasattr(res, "content") and getattr(res, "content", None):
            first_item = res.content[0]  # type: ignore[union-attr]
            if hasattr(first_item, "text"):
                return str(first_item.text)
        return str(res)


def _adapt_tool_to_langchain(name: str, description: str) -> StructuredTool:
    """Convert an MCP tool metadata into a LangChain StructuredTool.

    Args:
        name: Tool name.
        description: Description of tool purpose.

    Returns:
        StructuredTool callable by LangChain agent.
    """
    def _tool_func(query: str = "", **kwargs: Any) -> str:
        args = {"query": query} if query else kwargs
        return invoke_mcp_tool(name, args)

    return StructuredTool.from_function(
        func=_tool_func,
        name=name,
        description=description,
    )


def get_mcp_tools() -> list[BaseTool]:
    """Discover tools from the MCP server and return permitted LangChain tools.

    Returns:
        List of StructuredTool instances filtered by the application allowlist.
    """
    raw_tools = _run_sync(local_mcp_server.list_tools())
    adapted_tools: list[BaseTool] = []

    for tool_item in raw_tools:
        if check_tool_allowed(tool_item.name):
            adapted_tools.append(
                _adapt_tool_to_langchain(
                    name=tool_item.name,
                    description=tool_item.description or "",
                )
            )

    return adapted_tools
