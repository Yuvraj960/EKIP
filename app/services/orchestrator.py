"""app.services.orchestrator — Central request orchestrator and router.

Routes incoming user queries to the RAG answer pipeline or the bounded
action agent based on query classification.

Usage:
    from app.services.orchestrator import handle_query
    response = handle_query("Where is OAuth documented?")
"""

from langsmith import traceable

from app.agents.agent import run_agent
from app.api.schemas import AnswerResponse, EvidenceStatus, QueryType
from app.chains.answer import answer_question
from app.chains.classify import classify_query
from app.core.tracing import (
    META_CITATIONS_COUNT,
    META_EVIDENCE_STATUS,
    META_LAYER,
    META_MODULE,
    META_QUERY_TYPE,
    RUN_TYPE_CHAIN,
    TAG_EKIP,
    TAG_ORCHESTRATOR,
    add_trace_metadata,
    add_trace_tags,
    set_trace_name,
)
from app.retrieval.context import extract_citations
from app.retrieval.retriever import retrieve_chunks

AGENT_CONFIDENCE_NOTE: str = (
    "This is a draft produced by the agent. Please review before use."
)
NO_ACTION_EVIDENCE_ANSWER: str = (
    "I do not have enough relevant engineering runbook documentation "
    "in the indexed corpus to perform this action or draft this checklist."
)
NO_ACTION_EVIDENCE_NOTE: str = (
    "Action rejected: No supporting documentation found in the indexed corpus."
)
REFUSAL_PHRASES: tuple[str, ...] = (
    "do not have access",
    "no relevant runbook",
    "not found",
    "cannot find",
    "insufficient",
    "apologize",
    "not have documented",
)


def _handle_action_request(
    clean_query: str,
    top_k: int | None = None,
) -> AnswerResponse:
    """Execute bounded agent action with pre-flight relevance check and evidence grading.

    Args:
        clean_query: Cleaned user action request query.
        top_k: Optional chunk count limit.

    Returns:
        AnswerResponse with agent output, citations, and validated evidence status.
    """
    supporting_chunks = retrieve_chunks(clean_query, top_k=top_k or 3)
    if not supporting_chunks:
        return AnswerResponse(
            answer=NO_ACTION_EVIDENCE_ANSWER,
            citations=[],
            evidence_status=EvidenceStatus.INSUFFICIENT,
            confidence_note=NO_ACTION_EVIDENCE_NOTE,
        )

    agent_output = run_agent(clean_query)
    output_lower = agent_output.lower()
    is_missing = any(phrase in output_lower for phrase in REFUSAL_PHRASES)

    if is_missing:
        return AnswerResponse(
            answer=agent_output,
            citations=[],
            evidence_status=EvidenceStatus.INSUFFICIENT,
            confidence_note=AGENT_CONFIDENCE_NOTE,
        )

    citations = extract_citations(supporting_chunks)
    return AnswerResponse(
        answer=agent_output,
        citations=citations,
        evidence_status=EvidenceStatus.SUFFICIENT,
        confidence_note=AGENT_CONFIDENCE_NOTE,
    )


@traceable(
    name="EKIP Query Execution",
    run_type=RUN_TYPE_CHAIN,
    tags=[TAG_EKIP, TAG_ORCHESTRATOR],
    metadata={META_MODULE: "app.services.orchestrator", META_LAYER: "orchestrator"},
)
def handle_query(
    query: str,
    top_k: int | None = None,
) -> AnswerResponse:
    """Route a user query to RAG answer generation or the bounded agent.

    Args:
        query: User's question or command string.
        top_k: Optional maximum count of chunks to retrieve for context.

    Returns:
        AnswerResponse with synthesized answer, citations, and evidence status.
    """
    clean_query = query.strip()
    set_trace_name(f"EKIP Query: {clean_query[:45]}")
    add_trace_metadata({"user_query": clean_query})

    query_type = classify_query(clean_query)
    add_trace_tags([f"query_type:{query_type.value}"])
    add_trace_metadata({META_QUERY_TYPE: query_type.value})

    if query_type == QueryType.ACTION_REQUEST:
        response = _handle_action_request(clean_query, top_k=top_k)
    else:
        response = answer_question(clean_query, top_k=top_k)

    add_trace_tags([f"evidence:{response.evidence_status.value}"])
    add_trace_metadata(
        {
            META_EVIDENCE_STATUS: response.evidence_status.value,
            META_CITATIONS_COUNT: len(response.citations),
        }
    )
    return response
