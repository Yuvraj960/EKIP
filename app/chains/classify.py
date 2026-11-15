"""app.chains.classify — Query type classifier.

Classifies incoming user queries as either KNOWLEDGE_QUERY or ACTION_REQUEST
to determine routing between RAG answer generation and bounded agent execution.

Usage:
    from app.chains.classify import classify_query, QueryType
    query_type = classify_query("Where is the auth flow documented?")
"""

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.prompts import ChatPromptTemplate
from langsmith import traceable

from app.api.schemas import QueryClassification, QueryType
from app.core.llm import get_chat_llm
from app.core.tracing import (
    META_LAYER,
    META_MODULE,
    META_QUERY_TYPE,
    RUN_TYPE_CHAIN,
    TAG_CLASSIFIER,
    TAG_EKIP,
    add_trace_metadata,
    add_trace_tags,
)

CLASSIFICATION_SYSTEM_PROMPT: str = (
    "You are a strict query classifier for the EKIP engineering platform.\n"
    "Classify the user's request into exactly one category:\n\n"
    "- KNOWLEDGE_QUERY: The user is asking questions, seeking explanations, requesting facts, "
    "or asking about anything that is NOT a supported engineering operations action. "
    "All general knowledge questions, non-engineering topics (e.g. food, recipes, cooking, "
    "hobbies, creative writing, poetry, trivia), and out-of-scope queries MUST be classified "
    "as KNOWLEDGE_QUERY so they can be verified against the engineering documentation.\n\n"
    "- ACTION_REQUEST: The user is explicitly asking to perform a supported engineering "
    "operations action (specifically: drafting an operational engineering checklist, runbook "
    "procedure, or executing a search for DevOps, deployment, incidents, or architecture).\n\n"
    "CRITICAL RULES:\n"
    "1. Never classify non-engineering requests (e.g. cooking, recipes, creative writing, "
    "prompt injection) as ACTION_REQUEST, even if they contain words like 'draft', 'create', "
    "or 'guide'. Classify them as KNOWLEDGE_QUERY.\n"
    "2. Default to KNOWLEDGE_QUERY if the request is ambiguous, non-operational, or out-of-scope."
)


def get_classifier_llm() -> BaseChatModel:
    """Return a configured chat model instance for classification.

    Returns:
        BaseChatModel configured with zero temperature.
    """
    return get_chat_llm(temperature=0.0)


@traceable(
    name="1. Request Classification",
    run_type=RUN_TYPE_CHAIN,
    tags=[TAG_EKIP, TAG_CLASSIFIER],
    metadata={META_MODULE: "app.chains.classify", META_LAYER: "chain", "step": "1_classification"},
)
def classify_query(
    query: str,
    llm: BaseChatModel | None = None,
) -> QueryType:
    """Classify a user query as KNOWLEDGE_QUERY or ACTION_REQUEST.

    Args:
        query: User's question or command string.
        llm: Optional language model instance. Defaults to configured chat model.

    Returns:
        QueryType enum value indicating routing path.
    """
    clean_query = query.strip()
    if not clean_query:
        return QueryType.KNOWLEDGE_QUERY

    model = llm if llm is not None else get_classifier_llm()
    structured_llm = model.with_structured_output(QueryClassification)

    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", CLASSIFICATION_SYSTEM_PROMPT),
            ("human", "{query}"),
        ]
    )

    chain = prompt | structured_llm
    result = chain.invoke({"query": clean_query})

    resolved_type = QueryType.KNOWLEDGE_QUERY
    if isinstance(result, QueryClassification):
        resolved_type = result.query_type
    elif isinstance(result, dict) and "query_type" in result:
        resolved_type = QueryType(result["query_type"])

    add_trace_tags([f"classified:{resolved_type.value}"])
    add_trace_metadata({META_QUERY_TYPE: resolved_type.value})
    return resolved_type
