"""mcp_server.server — Standalone MCP server exposing knowledge search tools.

Exposes engineering knowledge search tools over the Model Context Protocol (MCP).
Runs as a separate service or stdio process connected to by app/mcp/client.py.

Tools:
    search_runbook(query: str) -> str: Searches indexed documents for runbook content.

Usage:
    python -m mcp_server.server
"""

from mcp.server.mcpserver import MCPServer

from app.retrieval.context import format_context
from app.retrieval.retriever import retrieve_chunks

SERVER_NAME: str = "ekip-knowledge-server"
NO_CONTENT_MSG: str = "No relevant runbook content found for this query."

mcp = MCPServer(SERVER_NAME)


@mcp.tool()
def search_runbook(query: str) -> str:
    """Search indexed engineering documents for runbook content.

    Args:
        query: Search term or question about operational runbooks or procedures.

    Returns:
        Formatted passages with source citations, or fallback text if not found.
    """
    clean_query = query.strip()
    if not clean_query:
        return NO_CONTENT_MSG

    chunks = retrieve_chunks(clean_query)
    if not chunks:
        return NO_CONTENT_MSG

    return format_context(chunks)


def main() -> None:
    """Run the MCP server over standard input/output transport."""
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
