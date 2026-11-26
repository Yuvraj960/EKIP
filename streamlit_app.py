"""streamlit_app — Streamlit chat UI for EKIP with multi-archive partitioning.

Provides a zip-first document upload and automatic ingestion flow, transitioning
into an interactive chat interface to ask questions against indexed engineering
documents with evidence status and verifiable source citations.

Usage:
    ekip start
    # or: uv run streamlit run streamlit_app.py
"""

from typing import Any

import httpx
import streamlit as st

from app.api.schemas import AnswerResponse, EvidenceStatus
from app.core.config import settings
from app.ingestion.archive_manager import clear_all_indexed_data, list_indexed_archives
from app.ingestion.zip_handler import ingest_zip_archive
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


def _render_sidebar_corpus(archives: list[dict[str, Any]]) -> None:
    """Render details of active sub-database archives in the sidebar.

    Args:
        archives: List of archive metadata dictionaries.
    """
    st.markdown("**Active Corpus (Partitioned Sub-DBs):**")
    if not archives:
        st.caption("No archives currently indexed.")
        return

    total_chunks = sum(a.get("chunk_count", 0) for a in archives)
    total_docs = sum(a.get("doc_count", 0) for a in archives)
    st.caption(f"**{len(archives)} Archive(s)** ({total_chunks} chunks, {total_docs} docs)")

    for arc in archives:
        name = arc.get("archive_name") or arc.get("slug")
        chunks = arc.get("chunk_count", 0)
        docs = arc.get("doc_count", 0)
        st.markdown(f"• **`{name}`** ({chunks} chunks, {docs} docs)")


def _render_sidebar() -> int:
    """Render sidebar controls and active corpus status.

    Returns:
        Integer top_k retrieval parameter.
    """
    with st.sidebar:
        st.header("⚙️ Configuration")
        if st.button("➕ Add / Manage Archives", use_container_width=True):
            st.session_state["ingested"] = False
            st.rerun()

        if st.button("🗑️ Clear Database & Reset", use_container_width=True):
            clear_all_indexed_data()
            st.session_state["ingested"] = False
            st.session_state["messages"] = []
            st.rerun()

        st.markdown("---")
        top_k = st.slider(
            "Retrieval Top-K",
            min_value=1,
            max_value=10,
            value=settings.retrieval_top_k,
        )
        st.markdown("---")
        _render_sidebar_corpus(list_indexed_archives())

        st.markdown("---")
        st.markdown("**Active Models & Engines:**")
        st.caption(f"LLM: `{settings.inference_model}` ({settings.inference_engine.value})")
        st.caption(f"Embeddings: `{settings.embedding_model}` ({settings.embedding_engine.value})")
    return top_k


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


def _handle_chat_query(prompt: str, top_k: int) -> None:
    """Process user prompt, generate grounded response, and update session history.

    Args:
        prompt: User input question or command.
        top_k: Number of chunks to retrieve.
    """
    st.session_state["messages"].append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Retrieving evidence across sub-databases and formulating answer..."):
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


def _process_zip_upload(uploaded_file: Any, clear_previous: bool) -> None:
    """Unzip uploaded file, chunk into partitioned sub-database, and enter chat.

    Args:
        uploaded_file: Uploaded file object from st.file_uploader.
        clear_previous: Whether to clear prior archives before ingestion.
    """
    file_bytes = uploaded_file.getvalue()
    with st.spinner(f"Indexing into sub-database '{uploaded_file.name}' in ChromaDB..."):
        try:
            doc_count, chunk_count, slug = ingest_zip_archive(
                file_bytes,
                archive_name=uploaded_file.name,
                clear_previous=clear_previous,
            )
        except ValueError as err:
            st.error(f"Archive error: {err}")
            return

    if chunk_count > 0:
        st.session_state["ingested"] = True
        st.session_state["messages"] = []
        st.success(
            f"Successfully partitioned {chunk_count} chunks from {doc_count} "
            f"documents into sub-database '{slug}'!"
        )
        st.rerun()
    else:
        st.warning("Archive extracted, but no supported document files were discovered.")


def _render_existing_archives_card(archives: list[dict[str, Any]]) -> None:
    """Display active sub-database archives list with a clear button.

    Args:
        archives: List of active archive metadata records.
    """
    st.markdown("### 📚 Currently Indexed Sub-Databases")
    for arc in archives:
        name = arc.get("archive_name") or arc.get("slug")
        chunks = arc.get("chunk_count", 0)
        docs = arc.get("doc_count", 0)
        st.markdown(f"- 📁 **`{name}`** — `{chunks}` chunks from `{docs}` documents")

    if st.button("🗑️ Clear Previous Data (Wipe All Sub-Databases)", use_container_width=True):
        clear_all_indexed_data()
        st.session_state["messages"] = []
        st.success("All previous vector databases and references have been cleared!")
        st.rerun()

    st.markdown("---")


def _render_upload_view() -> None:
    """Render the initial landing view dedicated to partitioned zip uploads."""
    st.title("📦 EKIP — Document Ingestion")
    st.markdown(
        "Upload a `.zip` archive to create a dedicated sub-database in ChromaDB. "
        "Supports **Markdown, PDF, Word (.docx), CSV, HTML, TXT, JSON, YAML, and RST**."
    )
    st.markdown("---")

    existing_archives = list_indexed_archives()
    if existing_archives:
        _render_existing_archives_card(existing_archives)

    uploaded = st.file_uploader(
        "Choose an engineering documentation archive (.zip)",
        type=["zip"],
        help="ZIP archive to index into its own named sub-database.",
    )

    if uploaded is not None:
        st.info(f"Selected archive: **{uploaded.name}** ({len(uploaded.getvalue()) / 1024:.1f} KB)")
        clear_first = st.checkbox("Clear previous databases before indexing this archive", False)
        if st.button("🚀 Ingest into Sub-Database", type="primary", use_container_width=True):
            _process_zip_upload(uploaded, clear_previous=clear_first)

    st.markdown("---")
    if st.button("⚡ Continue with previously indexed documents", use_container_width=True):
        if not existing_archives:
            st.warning("No indexed documents found in database. Please upload a .zip file first.")
        else:
            st.session_state["ingested"] = True
            st.rerun()


def _render_chat_view() -> None:
    """Render the main interactive chat assistant view."""
    st.title(f"{PAGE_ICON} EKIP Knowledge Assistant")
    st.caption("Grounded answers from engineering documentation with verifiable citations.")

    top_k = _render_sidebar()

    if "messages" not in st.session_state:
        st.session_state["messages"] = []

    _render_chat_history()

    prompt = st.chat_input("Ask about architecture, deployments, auth, or runbooks...")
    if prompt:
        _handle_chat_query(prompt, top_k)


def main() -> None:
    """Application entry point routing between upload landing screen and chat view."""
    st.set_page_config(page_title=PAGE_TITLE, page_icon=PAGE_ICON, layout="centered")

    if not st.session_state.get("ingested", False):
        _render_upload_view()
    else:
        _render_chat_view()


if __name__ == "__main__":
    main()
