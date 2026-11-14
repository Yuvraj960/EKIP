"""app.core.tracing — Centralized LangSmith tracing utilities and metadata helpers.

Provides standardized configuration, decorators, and dynamic run-tree annotation
helpers (tags, metadata, run types) for end-to-end observability across EKIP.

Usage:
    from app.core.tracing import add_trace_metadata, add_trace_tags
    add_trace_tags(["status:success"])
    add_trace_metadata({"chunks_count": 5})
"""

import os
from typing import Any, Literal

from langsmith import get_current_run_tree

from app.core.config import settings

# --- Run Type Constants ---
RunType = Literal["tool", "chain", "llm", "retriever", "embedding", "prompt", "parser"]

RUN_TYPE_CHAIN: RunType = "chain"
RUN_TYPE_LLM: RunType = "llm"
RUN_TYPE_RETRIEVER: RunType = "retriever"
RUN_TYPE_TOOL: RunType = "tool"
RUN_TYPE_PROMPT: RunType = "prompt"
RUN_TYPE_PARSER: RunType = "parser"

# --- Common Tag Constants ---
TAG_EKIP: str = "ekip"
TAG_ORCHESTRATOR: str = "orchestrator"
TAG_CLASSIFIER: str = "classifier"
TAG_RAG: str = "rag"
TAG_RETRIEVER: str = "retriever"
TAG_AGENT: str = "agent"
TAG_TOOL: str = "tool"
TAG_MCP: str = "mcp"
TAG_INGESTION: str = "ingestion"
TAG_EVAL: str = "eval"
TAG_API: str = "api"

# --- Common Metadata Keys ---
META_MODULE: str = "module"
META_LAYER: str = "layer"
META_PROJECT: str = "project"
META_QUERY_TYPE: str = "query_type"
META_EVIDENCE_STATUS: str = "evidence_status"
META_CITATIONS_COUNT: str = "citations_count"
META_CHUNKS_COUNT: str = "chunks_count"
META_TOOL_NAME: str = "tool_name"
META_LATENCY_SEC: str = "latency_sec"


def configure_tracing() -> None:
    """Synchronize application settings to environment variables for LangSmith.

    Ensures both LangChain and LangSmith SDK runtimes detect project name,
    API credentials, and tracing enablement flags consistently.
    """
    if settings.langsmith_api_key:
        os.environ["LANGSMITH_API_KEY"] = settings.langsmith_api_key
    if settings.langsmith_project:
        os.environ["LANGSMITH_PROJECT"] = settings.langsmith_project
        os.environ["LANGCHAIN_PROJECT"] = settings.langsmith_project
    if settings.langsmith_endpoint:
        os.environ["LANGSMITH_ENDPOINT"] = settings.langsmith_endpoint

    tracing_val = "true" if settings.langsmith_tracing else "false"
    os.environ["LANGSMITH_TRACING"] = tracing_val
    os.environ["LANGCHAIN_TRACING_V2"] = tracing_val


def add_trace_tags(tags: list[str]) -> None:
    """Safely append tags to the active LangSmith run tree if tracing is active.

    Args:
        tags: List of string labels to attach to the current run.
    """
    try:
        run_tree = get_current_run_tree()
        if run_tree is not None:
            if run_tree.tags is None:
                run_tree.tags = []
            existing_tags = set(run_tree.tags)
            for tag in tags:
                if tag not in existing_tags:
                    run_tree.tags.append(tag)
                    existing_tags.add(tag)
    except Exception:
        # Tracing helpers must never disrupt application execution
        pass


def add_trace_metadata(metadata: dict[str, Any]) -> None:
    """Safely merge metadata into the active LangSmith run tree.

    Args:
        metadata: Dictionary of key-value attributes to attach to current run.
    """
    try:
        run_tree = get_current_run_tree()
        if run_tree is not None:
            if run_tree.metadata is None:
                run_tree.metadata = {}
            run_tree.metadata.update(metadata)
    except Exception:
        # Tracing helpers must never disrupt application execution
        pass


def set_trace_name(name: str) -> None:
    """Safely override the name of the active LangSmith run tree.

    Args:
        name: New human-readable identifier for the current trace span.
    """
    try:
        run_tree = get_current_run_tree()
        if run_tree is not None:
            run_tree.name = name
    except Exception:
        pass


# Automatically configure tracing environment variables on module import
configure_tracing()
