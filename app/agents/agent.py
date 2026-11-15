"""app.agents.agent — Bounded LangChain agent with allowlist enforcement.

Executes ACTION_REQUEST queries (such as runbook search and checklist drafting)
while strictly verifying every tool invocation against the permission allowlist.

Usage:
    from app.agents.agent import run_agent
    result = run_agent("Draft a deployment rollback checklist")
"""

from typing import Any

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import (
    BaseMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)
from langchain_core.tools import BaseTool
from langsmith import traceable

from app.agents.tools import draft_checklist
from app.chains.answer import get_rag_llm
from app.core.permissions import assert_tool_allowed
from app.core.tracing import (
    META_LAYER,
    META_MODULE,
    META_TOOL_NAME,
    RUN_TYPE_CHAIN,
    RUN_TYPE_LLM,
    RUN_TYPE_TOOL,
    TAG_AGENT,
    TAG_EKIP,
    TAG_TOOL,
    add_trace_metadata,
    add_trace_tags,
    set_trace_name,
)
from app.mcp.client import get_mcp_tools

AGENT_SYSTEM_PROMPT: str = (
    "You are a bounded operations assistant for EKIP engineering platform.\n"
    "Your capabilities are strictly limited to engineering operational procedures "
    "documented in indexed runbooks.\n\n"
    "Guidelines:\n"
    "1. For checklist requests, first use `search_runbook` to find documented procedures.\n"
    "2. Next, use `draft_checklist` with the retrieved context to produce the checklist.\n"
    "3. If no relevant runbook content exists or the request is outside engineering operations, "
    "explicitly state that you do not have documented engineering procedures to perform it.\n"
    "4. You do NOT possess write access to production systems.\n"
    "5. All outputs must be clearly designated as DRAFTS for human engineer review."
)
MAX_AGENT_ITERATIONS: int = 5


@traceable(
    name="2.1 Agent Tool Execution",
    run_type=RUN_TYPE_TOOL,
    tags=[TAG_EKIP, TAG_AGENT, TAG_TOOL],
    metadata={META_MODULE: "app.agents.agent", "step": "2.1_tool_execution"},
)
def _execute_tool_call(
    tool_call: dict[str, Any],
    tool_map: dict[str, BaseTool],
) -> ToolMessage:
    """Validate tool permissions and execute an individual tool call.

    Args:
        tool_call: Dict holding tool name, arguments, and ID.
        tool_map: Mapping of tool names to BaseTool instances.

    Returns:
        ToolMessage with tool execution result or error description.

    Raises:
        PermissionError: If the requested tool is not on the allowlist.
    """
    tool_name = tool_call["name"]
    call_id = tool_call.get("id", "tool_call_id")
    args = tool_call.get("args", {})

    set_trace_name(f"Tool: {tool_name}")
    add_trace_tags([f"tool:{tool_name}"])
    add_trace_metadata({META_TOOL_NAME: tool_name, "call_id": call_id})

    assert_tool_allowed(tool_name)

    target_tool = tool_map.get(tool_name)
    if target_tool is None:
        raise PermissionError(f"Tool '{tool_name}' is allowlisted but not implemented.")

    output = target_tool.invoke(args)
    return ToolMessage(content=str(output), tool_call_id=call_id)


@traceable(
    name="2.2 Agent Planning (LLM)",
    run_type=RUN_TYPE_LLM,
    tags=[TAG_EKIP, TAG_AGENT, "llm"],
    metadata={META_MODULE: "app.agents.agent"},
)
def _invoke_agent_llm(model_with_tools: Any, messages: list[BaseMessage]) -> Any:
    """Invoke the tool-bound model with a traceable LLM span.

    Args:
        model_with_tools: Chat model bound with tools.
        messages: Conversation history.

    Returns:
        Model response message.
    """
    return model_with_tools.invoke(messages)


def _format_ai_content(content: Any) -> str:
    """Extract clean string text from AI message content.

    Args:
        content: String or list representation of AI output message.

    Returns:
        Formatted markdown string text.
    """
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, dict) and "text" in item:
                parts.append(str(item["text"]))
            elif isinstance(item, str):
                parts.append(item)
            else:
                parts.append(str(item))
        return "\n".join(parts).strip()
    return str(content)


def _run_agent_loop(
    messages: list[BaseMessage],
    model_with_tools: Any,
    tool_map: dict[str, BaseTool],
    max_iterations: int = MAX_AGENT_ITERATIONS,
) -> str:
    """Run iterative tool-calling loop until a final response is generated.

    Args:
        messages: Conversation history messages.
        model_with_tools: Chat model bound with tools.
        tool_map: Mapping from tool name to tool callable.
        max_iterations: Maximum tool invocation rounds.

    Returns:
        Final response text from the agent.
    """
    for _ in range(max_iterations):
        ai_response = _invoke_agent_llm(model_with_tools, messages)
        messages.append(ai_response)

        tool_calls = getattr(ai_response, "tool_calls", None)
        if not tool_calls:
            return _format_ai_content(ai_response.content)

        for call in tool_calls:
            tool_msg = _execute_tool_call(call, tool_map)
            messages.append(tool_msg)

    return "Agent reached maximum iteration limit without finalizing response."


def get_agent_tools() -> list[BaseTool]:
    """Retrieve the full agent toolset combining MCP tools and local tools.

    Returns:
        List of permitted BaseTool instances.
    """
    mcp_tools = get_mcp_tools()
    return [*mcp_tools, draft_checklist]


@traceable(
    name="2. Bounded Agent Execution",
    run_type=RUN_TYPE_CHAIN,
    tags=[TAG_EKIP, TAG_AGENT],
    metadata={META_MODULE: "app.agents.agent", META_LAYER: "agent", "step": "2_agent_execution"},
)
def run_agent(
    query: str,
    llm: BaseChatModel | None = None,
    tools: list[BaseTool] | None = None,
) -> str:
    """Run the bounded agent for an action request with tool allowlist checks.

    Args:
        query: User action request string.
        llm: Optional BaseChatModel instance.
        tools: Optional list of BaseTool objects. Defaults to get_agent_tools().

    Returns:
        Draft response text produced by the agent.
    """
    clean_query = query.strip()
    if not clean_query:
        return "No action request provided."

    active_tools = tools if tools is not None else get_agent_tools()
    tool_map = {t.name: t for t in active_tools}

    add_trace_metadata(
        {
            "tools_count": len(active_tools),
            "tool_names": list(tool_map.keys()),
        }
    )

    model = llm if llm is not None else get_rag_llm()
    model_with_tools = model.bind_tools(active_tools)

    messages: list[BaseMessage] = [
        SystemMessage(content=AGENT_SYSTEM_PROMPT),
        HumanMessage(content=clean_query),
    ]

    return _run_agent_loop(messages, model_with_tools, tool_map)
