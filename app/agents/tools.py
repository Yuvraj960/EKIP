"""app.agents.tools — Bounded agent tool implementations.

Provides read-only and draft-only tools for the agent:
    1. search_runbook: Queries indexed engineering docs and returns formatted context.
    2. draft_checklist: Drafts a structured markdown checklist based on retrieved context.
    
Usage:
    from app.agents.tools import search_runbook, draft_checklist
    context = search_runbook.invoke({"query": "rollback"})
"""

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tools import tool
from langsmith import traceable

from app.chains.answer import get_rag_llm
from app.core.permissions import assert_tool_allowed
from app.core.tracing import (
    META_MODULE,
    RUN_TYPE_LLM,
    RUN_TYPE_TOOL,
    TAG_EKIP,
    TAG_TOOL,
    add_trace_metadata,
)
from app.retrieval.context import format_context
from app.retrieval.retriever import retrieve_chunks

NO_RUNBOOK_FOUND: str = "No relevant runbook content found for this query."
CHECKLIST_SYSTEM_PROMPT: str = (
    "You are a DevOps engineering assistant drafting an operational checklist.\n"
    "Draft a concise, step-by-step checklist using markdown checkboxes (`- [ ]`).\n"
    "Ground every step in the provided context evidence where available.\n"
    "Always prepend a note that this is a DRAFT requiring human engineer review."
)


@tool
@traceable(
    name="tools.search_runbook",
    run_type=RUN_TYPE_TOOL,
    tags=[TAG_EKIP, TAG_TOOL, "search_runbook"],
    metadata={META_MODULE: "app.agents.tools"},
)
def search_runbook(query: str) -> str:
    """Search indexed runbooks and engineering docs for information about a topic.

    Args:
        query: Search term or question about procedures, runbooks, or architecture.

    Returns:
        Formatted context string containing relevant passages with source citations.
    """
    assert_tool_allowed("search_runbook")
    clean_query = query.strip()
    if not clean_query:
        return NO_RUNBOOK_FOUND

    chunks = retrieve_chunks(clean_query)
    if not chunks:
        return NO_RUNBOOK_FOUND

    add_trace_metadata({"chunks_retrieved": len(chunks)})
    return format_context(chunks)


@traceable(
    name="tools.generate_checklist",
    run_type=RUN_TYPE_LLM,
    tags=[TAG_EKIP, TAG_TOOL, "checklist_llm"],
    metadata={META_MODULE: "app.agents.tools"},
)
def _generate_checklist(
    task_description: str,
    context: str,
    llm: BaseChatModel | None = None,
) -> str:
    """Generate markdown checklist text using the language model.

    Args:
        task_description: Goal or procedure name for the checklist.
        context: Supporting documentation context.
        llm: Optional BaseChatModel instance.

    Returns:
        Markdown string checklist.
    """
    model = llm if llm is not None else get_rag_llm()
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", CHECKLIST_SYSTEM_PROMPT),
            (
                "human",
                "Task: {task_description}\n\nDocumentation Context:\n{context}",
            ),
        ]
    )
    chain = prompt | model
    result = chain.invoke(
        {"task_description": task_description, "context": context}
    )
    return str(result.content)


@tool
@traceable(
    name="tools.draft_checklist",
    run_type=RUN_TYPE_TOOL,
    tags=[TAG_EKIP, TAG_TOOL, "draft_checklist"],
    metadata={META_MODULE: "app.agents.tools"},
)
def draft_checklist(task_description: str, context: str) -> str:
    """Draft a markdown checklist for a task based on provided context.

    Args:
        task_description: What the checklist is for (e.g. 'Canary Rollback').
        context: Relevant documentation excerpts to base the checklist steps on.

    Returns:
        Draft markdown checklist for human review before execution.
    """
    assert_tool_allowed("draft_checklist")
    add_trace_metadata(
        {
            "task_description": task_description,
            "context_chars": len(context),
        }
    )
    return _generate_checklist(task_description, context)


AGENT_TOOLS = [search_runbook, draft_checklist]
