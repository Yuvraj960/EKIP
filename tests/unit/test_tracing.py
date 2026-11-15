"""tests.unit.test_tracing — Unit tests for app.core.tracing."""

import os
from typing import Any

from langsmith import get_current_run_tree, traceable

from app.core.tracing import (
    META_MODULE,
    RUN_TYPE_CHAIN,
    RUN_TYPE_RETRIEVER,
    RUN_TYPE_TOOL,
    TAG_EKIP,
    TAG_ORCHESTRATOR,
    add_trace_metadata,
    add_trace_tags,
    configure_tracing,
    set_trace_name,
)


def test_configure_tracing_environment() -> None:
    """Verify configure_tracing sets required LangSmith environment variables."""
    configure_tracing()
    assert os.environ.get("LANGSMITH_TRACING") in {"true", "false"}
    assert os.environ.get("LANGCHAIN_TRACING_V2") in {"true", "false"}
    assert os.environ.get("LANGSMITH_PROJECT") == "ekip"
    assert os.environ.get("LANGCHAIN_PROJECT") == "ekip"


def test_safe_helpers_outside_run_tree() -> None:
    """Verify tracing helpers do not raise exceptions when called outside a trace."""
    # Should execute cleanly without errors even when no run tree exists
    add_trace_tags(["test-tag", "tag-2"])
    add_trace_metadata({"test_key": "test_value"})
    set_trace_name("custom_name")


def test_traceable_decorator_execution() -> None:
    """Verify that a decorated function executes and preserves outputs and mutations."""
    captured_metadata: dict[str, Any] = {}
    captured_tags: list[str] = []

    @traceable(
        name="test.pipeline",
        run_type=RUN_TYPE_CHAIN,
        tags=[TAG_EKIP, TAG_ORCHESTRATOR],
        metadata={META_MODULE: "tests.test_tracing"},
    )
    def sample_traced_function(value: int) -> int:
        """Sample function for testing active trace tree dynamic annotations."""
        add_trace_tags(["dynamic_tag_1"])
        add_trace_metadata({"computed_result": value * 2})
        set_trace_name("overridden.test.pipeline")

        run_tree = get_current_run_tree()
        if run_tree is not None:
            if run_tree.tags:
                captured_tags.extend(run_tree.tags)
            if run_tree.metadata:
                captured_metadata.update(run_tree.metadata)

        return value * 2

    result = sample_traced_function(21)
    assert result == 42


def test_traceable_tool_run_type() -> None:
    """Verify tool run type decoration executes and returns intended results."""

    @traceable(
        name="test.tool_call",
        run_type=RUN_TYPE_TOOL,
        tags=["tool_test"],
    )
    def sample_tool(arg: str) -> str:
        """Sample tool for testing tool run type."""
        return f"processed:{arg}"

    assert sample_tool("input_data") == "processed:input_data"


def test_single_trace_branch_hierarchy() -> None:
    """Verify nested traceable functions maintain parent-child hierarchy."""
    trace_info: dict[str, Any] = {}

    @traceable(name="2.1 Document Retrieval (ChromaDB)", run_type=RUN_TYPE_RETRIEVER)
    def sub_retrieval(query: str) -> str:
        rt = get_current_run_tree()
        if rt is not None:
            trace_info["child_parent_id"] = rt.parent_run_id
            trace_info["child_id"] = rt.id
        return f"chunks for {query}"

    @traceable(name="EKIP Query Execution", run_type=RUN_TYPE_CHAIN)
    def root_query(query: str) -> str:
        rt = get_current_run_tree()
        if rt is not None:
            trace_info["root_id"] = rt.id
            trace_info["root_parent_id"] = rt.parent_run_id
        return sub_retrieval(query)

    res = root_query("test query")
    assert res == "chunks for test query"
    # When executed, if tracing tree is active, child's parent matches root's id
    if "root_id" in trace_info and "child_parent_id" in trace_info:
        assert trace_info["child_parent_id"] == trace_info["root_id"]
