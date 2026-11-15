"""tests.unit.test_permissions — Unit tests for app.core.permissions."""

import pytest

from app.core.permissions import ALLOWED_TOOLS, assert_tool_allowed, check_tool_allowed


def test_allowed_tool_passes() -> None:
    """Verify that all allowlisted tools return True."""
    assert check_tool_allowed("search_runbook") is True
    assert check_tool_allowed("draft_checklist") is True


def test_unknown_tool_blocked() -> None:
    """Verify that unlisted tools return False."""
    assert check_tool_allowed("delete_all_data") is False
    assert check_tool_allowed("execute_shell") is False


def test_assert_raises_for_unlisted_tool() -> None:
    """Verify that assert_tool_allowed raises PermissionError for unlisted tool."""
    with pytest.raises(PermissionError, match="not in the allowed tool list"):
        assert_tool_allowed("run_shell_command")


def test_assert_passes_for_allowed_tool() -> None:
    """Verify that assert_tool_allowed does not raise for allowlisted tool."""
    assert_tool_allowed("search_runbook")
    assert_tool_allowed("draft_checklist")


def test_allowlist_is_frozen() -> None:
    """Verify that ALLOWED_TOOLS cannot be mutated at runtime."""
    with pytest.raises((AttributeError, TypeError)):
        ALLOWED_TOOLS.add("new_unauthorized_tool")  # type: ignore[attr-defined]
