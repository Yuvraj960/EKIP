"""app.chains.answer — RAG answer generation chain.

Composes chunk retrieval, context formatting, prompting, LLM invocation,
and Pydantic response validation into an LCEL pipeline.

Usage:
    from app.chains.answer import answer_question
    response = answer_question("What is the deployment procedure?")
"""

from typing import Any

from langchain_community.vectorstores import Chroma
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.prompts import ChatPromptTemplate
from langsmith import traceable

from app.api.schemas import AnswerResponse, EvidenceStatus
from app.core.llm import get_chat_llm
from app.core.tracing import (
    META_CITATIONS_COUNT,
    META_EVIDENCE_STATUS,
    META_LAYER,
    META_MODULE,
    RUN_TYPE_CHAIN,
    RUN_TYPE_LLM,
    TAG_EKIP,
    TAG_RAG,
    add_trace_metadata,
    add_trace_tags,
)
from app.retrieval.context import extract_citations, format_context
from app.retrieval.retriever import retrieve_chunks

RAG_SYSTEM_PROMPT: str = (
    "You are an AI assistant for the Engineering Knowledge Intelligence Platform (EKIP).\n"
    "Answer developer questions using ONLY the provided documentation evidence.\n\n"
    "Rules:\n"
    "1. Rely exclusively on the evidence provided in the user prompt.\n"
    "2. If evidence does not contain sufficient information, set evidence_status to "
    "'INSUFFICIENT' and state that the information was not found.\n"
    "3. If evidence only partially addresses the question, set evidence_status to 'PARTIAL' "
    "and explain missing aspects in confidence_note.\n"
    "4. If evidence fully answers the question, set evidence_status to 'SUFFICIENT'.\n"
    "5. Populate citations with source, section, and passage_excerpt for evidence used."
)

RAG_USER_PROMPT: str = (
    "Documentation Evidence:\n"
    "---\n"
    "{context}\n"
    "---\n\n"
    "Question: {question}"
)

INSUFFICIENT_ANSWER_FALLBACK: str = (
    "I do not have enough information in the indexed engineering documents "
    "to answer this question."
)


def get_rag_llm() -> BaseChatModel:
    """Return a configured chat model instance for RAG answers.

    Returns:
        BaseChatModel configured with zero temperature.
    """
    return get_chat_llm(temperature=0.0)


def _build_rag_chain(model: BaseChatModel):
    """Build LCEL prompt and structured output runnable chain.

    Args:
        model: Configured BaseChatModel instance.

    Returns:
        Runnable chain accepting {'context': str, 'question': str}.
    """
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", RAG_SYSTEM_PROMPT),
            ("human", RAG_USER_PROMPT),
        ]
    )
    return prompt | model.with_structured_output(AnswerResponse)


@traceable(
    name="2.3 Answer Generation (Gemini)",
    run_type=RUN_TYPE_LLM,
    tags=[TAG_EKIP, TAG_RAG, "synthesis"],
    metadata={META_MODULE: "app.chains.answer", "step": "2.3_synthesis"},
)
def _invoke_rag_llm(chain: Any, context_str: str, clean_query: str) -> Any:
    """Invoke the structured RAG chain with traceable LLM span.

    Args:
        chain: Runnable LCEL pipeline.
        context_str: Formatted context evidence text.
        clean_query: Sanitized user query string.

    Returns:
        Raw output from the model runnable.
    """
    return chain.invoke({"context": context_str, "question": clean_query})


@traceable(
    name="2. RAG Pipeline",
    run_type=RUN_TYPE_CHAIN,
    tags=[TAG_EKIP, TAG_RAG],
    metadata={META_MODULE: "app.chains.answer", META_LAYER: "chain", "step": "2_rag_pipeline"},
)
def answer_question(
    query: str,
    top_k: int | None = None,
    min_score: float | None = None,
    llm: BaseChatModel | None = None,
    store: Chroma | None = None,
) -> AnswerResponse:
    """Answer a user query using indexed document evidence.

    Args:
        query: User's question text.
        top_k: Optional limit on retrieved chunks. Defaults to config.
        min_score: Optional similarity threshold. Defaults to config.
        llm: Optional chat model override. Defaults to configured model.
        store: Optional vector store override. Defaults to configured Chroma store.

    Returns:
        Validated AnswerResponse with answer, citations, and evidence status.
    """
    clean_query = query.strip()
    if not clean_query:
        return AnswerResponse(
            answer=INSUFFICIENT_ANSWER_FALLBACK,
            citations=[],
            evidence_status=EvidenceStatus.INSUFFICIENT,
            confidence_note="Empty question provided.",
        )

    chunks = retrieve_chunks(clean_query, top_k=top_k, min_score=min_score, store=store)
    if not chunks:
        return AnswerResponse(
            answer=INSUFFICIENT_ANSWER_FALLBACK,
            citations=[],
            evidence_status=EvidenceStatus.INSUFFICIENT,
            confidence_note="No document chunks passed similarity threshold.",
        )

    context_str = format_context(chunks)
    model = llm if llm is not None else get_rag_llm()
    chain = _build_rag_chain(model)

    raw_response = _invoke_rag_llm(chain, context_str, clean_query)
    response = (
        raw_response
        if isinstance(raw_response, AnswerResponse)
        else AnswerResponse.model_validate(raw_response)
    )

    if not response.citations and response.evidence_status != EvidenceStatus.INSUFFICIENT:
        response.citations = extract_citations(chunks)

    add_trace_tags([f"evidence:{response.evidence_status.value}"])
    add_trace_metadata(
        {
            META_EVIDENCE_STATUS: response.evidence_status.value,
            META_CITATIONS_COUNT: len(response.citations),
            "sources_cited": [c.source for c in response.citations],
        }
    )
    return response
