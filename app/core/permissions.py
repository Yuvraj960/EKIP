"""app.core.permissions — Agent tool allowlist and permission enforcement.

Enforces application-level access control over agent tools. The agent may
only call tools explicitly registered in ALLOWED_TOOLS.

Usage:
    from app.core.permissions import assert_tool_allowed, check_tool_allowed
    assert_tool_allowed("search_runbook")
"""

ALLOWED_TOOLS: frozenset[str] = frozenset(
    {
        "search_runbook",
        "draft_checklist",
    }
)


def check_tool_allowed(tool_name: str) -> bool:
    """Check whether a tool name is permitted by the allowlist.

    Args:
        tool_name: Name of the tool to verify.

    Returns:
        True if the tool is in ALLOWED_TOOLS, False otherwise.
    """
    return tool_name in ALLOWED_TOOLS


def assert_tool_allowed(tool_name: str) -> None:
    """Validate that a tool is allowlisted, raising PermissionError if blocked.

    Args:
        tool_name: Name of the tool to verify.

    Raises:
        PermissionError: If the tool is not registered in ALLOWED_TOOLS.
    """
    if not check_tool_allowed(tool_name):
        allowed_list = sorted(ALLOWED_TOOLS)
        raise PermissionError(
            f"Tool '{tool_name}' is not in the allowed tool list. "
            f"Allowed tools: {allowed_list}"
        )
