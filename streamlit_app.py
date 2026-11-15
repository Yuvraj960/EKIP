"""streamlit_app — Streamlit chat UI for EKIP.

Provides an interactive chat interface to ask questions against indexed
engineering documents, review evidence status, and inspect source citations.

Usage:
    streamlit run streamlit_app.py
"""

from typing import Any

import httpx
import streamlit as st

from app.api.schemas import AnswerResponse, EvidenceStatus
from app.core.config import settings
from app.services.orchestrator import handle_query

PAGE_TITLE: str = "EKIP Assistant"
PAGE_ICON: str = "🤖"
API_URL: str = f"http://{settings.api_host}:{settings.api_port}"


def _get_status_badge(status: EvidenceStatus) -> str:
    """Return a markdown-formatted colored badge for evidence status.

    Args:
        status: EvidenceStatus enum value.

    Returns:
        Markdown string with colored label.
    """
    if status == EvidenceStatus.SUFFICIENT:
        return ":green[**[SUFFICIENT EVIDENCE]**]"
    if status == EvidenceStatus.PARTIAL:
        return ":orange[**[PARTIAL EVIDENCE]**]"
    return ":red[**[INSUFFICIENT EVIDENCE]**]"


def _query_backend(question: str, top_k: int) -> AnswerResponse:
    """Send question to FastAPI endpoint or fallback to direct orchestrator call.

    Args:
        question: User query string.
        top_k: Chunks retrieval limit.

    Returns:
        Validated AnswerResponse model.
    """
    endpoint = f"{API_URL}/ask"
    payload = {"question": question, "top_k": top_k}

    try:
        with httpx.Client(timeout=30.0) as client:
            resp = client.post(endpoint, json=payload)
            if resp.status_code == 200:
                return AnswerResponse.model_validate(resp.json())
    except (httpx.ConnectError, httpx.TimeoutException):
        pass

    return handle_query(question, top_k=top_k)


def _render_sidebar() -> int:
    """Render sidebar controls and return selected top_k value.

    Returns:
        Integer top_k retrieval parameter.
    """
    with st.sidebar:
        st.header("⚙️ Configuration")
        top_k = st.slider(
            "Retrieval Top-K",
            min_value=1,
            max_value=10,
            value=settings.retrieval_top_k,
        )
        st.markdown("---")
        st.markdown("**Active Models & Engines:**")
        st.caption(f"LLM: `{settings.inference_model}` ({settings.inference_engine.value})")
        st.caption(f"Embeddings: `{settings.embedding_model}` ({settings.embedding_engine.value})")
        st.markdown("---")
        st.markdown("**Indexed Corpus:**")
        st.caption("• Authentication Guide (OAuth2 / JWT)")
        st.caption("• Deployment Runbook (Rollback)")
        st.caption("• Incident Response (SLOs)")
        st.caption("• API Reference")
    return top_k


def _render_citations(citations: list[Any]) -> None:
    """Render expandable citations view for an answer.

    Args:
        citations: List of Citation schema models.
    """
    if not citations:
        return

    with st.expander(f"📚 View Sources & Citations ({len(citations)})"):
        for idx, citation in enumerate(citations, start=1):
            source = getattr(citation, "source", "")
            section = getattr(citation, "section", "")
            excerpt = getattr(citation, "passage_excerpt", "")
            st.markdown(f"**[{idx}] {source}** — *{section}*")
            st.info(f'"{excerpt}"')


def _render_chat_history() -> None:
    """Display past messages stored in session state."""
    for message in st.session_state.get("messages", []):
        with st.chat_message(message["role"]):
            if message["role"] == "assistant":
                status = message.get("evidence_status")
                if status:
                    st.markdown(_get_status_badge(status))
            st.markdown(message["content"])
            if message.get("citations"):
                _render_citations(message["citations"])


def main() -> None:
    """Initialize and run the Streamlit EKIP application."""
    st.set_page_config(page_title=PAGE_TITLE, page_icon=PAGE_ICON, layout="centered")
    st.title(f"{PAGE_ICON} EKIP Knowledge Assistant")
    st.caption("Grounded answers from engineering documentation with verifiable citations.")

    top_k = _render_sidebar()

    if "messages" not in st.session_state:
        st.session_state["messages"] = []

    _render_chat_history()

    prompt = st.chat_input("Ask about architecture, deployments, auth, or runbooks...")
    if not prompt:
        return

    st.session_state["messages"].append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Retrieving evidence and formulating answer..."):
            response = _query_backend(prompt, top_k=top_k)

        st.markdown(_get_status_badge(response.evidence_status))
        st.markdown(response.answer)
        if response.confidence_note:
            st.caption(f"Note: {response.confidence_note}")
        if response.citations:
            _render_citations(response.citations)

    st.session_state["messages"].append(
        {
            "role": "assistant",
            "content": response.answer,
            "evidence_status": response.evidence_status,
            "citations": response.citations,
        }
    )


if __name__ == "__main__":
    main()
