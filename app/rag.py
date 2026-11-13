"""RAG pipeline composed with LCEL: classify -> retrieve -> format -> prompt -> LLM -> validate."""
from functools import lru_cache
from operator import itemgetter

from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.runnables import (
    RunnableBranch,
    RunnableLambda,
    RunnableParallel,
    RunnablePassthrough,
)

from app.config import get_settings
from app.models import get_chat_model, get_vectorstore
from app.prompts import ANSWER_PROMPT, CLASSIFY_PROMPT
from app.schemas import ChatResponse, ChatTurn, QuestionType, RAGAnswer, SourceCitation

CANNED = {
    "chitchat": "Hi! Upload some documents and ask me questions about them. "
    "I'll answer from your files and show citations.",
    "out_of_scope": "I can only answer questions about your uploaded documents. "
    "Try asking something about their content.",
}


def format_docs(docs) -> str:
    if not docs:
        return "(no passages retrieved)"
    return "\n\n".join(
        f"[{d.metadata['chunk_id']}] ({d.metadata['title']} | {d.metadata['section']})\n{d.page_content}"
        for d in docs
    )


def to_history(turns: list[ChatTurn]):
    return [
        HumanMessage(t.content) if t.role == "user" else AIMessage(t.content)
        for t in turns
    ]


def _resolve(x: dict) -> ChatResponse:
    """Validate model output: keep only citations that point to retrieved chunks."""
    raw: RAGAnswer = x["raw"]
    by_id = {d.metadata["chunk_id"]: d for d in x["docs"]}
    cites, seen = [], set()
    for c in raw.citations:
        d = by_id.get(c.chunk_id)
        if d and c.chunk_id not in seen:
            seen.add(c.chunk_id)
            m = d.metadata
            cites.append(
                SourceCitation(
                    chunk_id=c.chunk_id,
                    source=m["source"],
                    title=m["title"],
                    section=m["section"],
                    doc_version=m["doc_version"],
                    quote=c.quote,
                )
            )
    status = raw.evidence_status
    if status != "insufficient" and not cites:  # uncited answer is not grounded
        status = "insufficient"
    return ChatResponse(
        answer=raw.answer,
        question_type="document_question",
        evidence_status=status,
        confidence=min(max(raw.confidence, 0.0), 1.0),
        citations=cites,
    )


def _canned(x: dict) -> ChatResponse:
    cat = x["classification"].category
    return ChatResponse(
        answer=CANNED.get(cat, CANNED["out_of_scope"]),
        question_type=cat,
        evidence_status="insufficient",
        confidence=1.0,
        citations=[],
    )


@lru_cache
def get_pipeline():
    llm = get_chat_model()
    retriever = get_vectorstore().as_retriever(
        search_type="similarity", search_kwargs={"k": get_settings().top_k}
    )

    classify = CLASSIFY_PROMPT | llm.with_structured_output(QuestionType)

    answer_chain = (
        RunnablePassthrough.assign(docs=itemgetter("question") | retriever)
        .assign(context=lambda x: format_docs(x["docs"]))
        | RunnableParallel(
            raw=ANSWER_PROMPT | llm.with_structured_output(RAGAnswer),
            docs=itemgetter("docs"),
        )
        | RunnableLambda(_resolve)
    )

    return RunnablePassthrough.assign(classification=classify) | RunnableBranch(
        (lambda x: x["classification"].category == "document_question", answer_chain),
        RunnableLambda(_canned),
    )
