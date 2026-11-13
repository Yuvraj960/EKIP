"""Streamlit chat UI. Talks to the FastAPI backend."""
import os

import requests
import streamlit as st

API = os.getenv("API_URL", "http://localhost:8000")
BADGE = {"supported": "🟢 Supported", "partial": "🟡 Partial", "insufficient": "🔴 Insufficient evidence"}

st.set_page_config(page_title="Docs Chatbot", page_icon="📄")
st.title("📄 Chat with your documents")

if "messages" not in st.session_state:
    st.session_state.messages = []


def render_assistant(msg: dict):
    st.markdown(msg["content"])
    if msg.get("question_type") == "document_question":
        st.caption(f"{BADGE[msg['evidence_status']]} · confidence {msg['confidence']:.0%}")
        if msg["citations"]:
            with st.expander(f"Sources ({len(msg['citations'])})"):
                for c in msg["citations"]:
                    st.markdown(
                        f"**{c['title']}** · {c['section']} · v`{c['doc_version']}`  \n"
                        f"> {c['quote']}"
                    )


# ---- Sidebar: ingestion ----------------------------------------------------
with st.sidebar:
    st.header("Documents")
    uploads = st.file_uploader(
        "Upload files", type=["pdf", "txt", "md", "docx"], accept_multiple_files=True
    )
    if st.button("Index documents", disabled=not uploads, use_container_width=True):
        with st.spinner("Chunking and embedding..."):
            try:
                r = requests.post(
                    f"{API}/ingest",
                    files=[("files", (f.name, f.getvalue())) for f in uploads],
                    timeout=600,
                )
                r.raise_for_status()
                out = r.json()
                for d in out["indexed"]:
                    st.success(f"{d['source']}: {d['chunks']} chunks")
                for e in out["errors"]:
                    st.error(f"{e['file']}: {e['error']}")
            except requests.RequestException as e:
                st.error(f"API error: {e}")

    st.subheader("Indexed")
    try:
        docs = requests.get(f"{API}/documents", timeout=10).json()
        for d in docs:
            st.write(f"• {d['source']} ({d['chunks']} chunks, v`{d['version']}`)")
        if not docs:
            st.caption("Nothing indexed yet.")
    except requests.RequestException:
        st.warning("Backend not reachable. Start the FastAPI server.")

    if st.button("Clear chat", use_container_width=True):
        st.session_state.messages = []
        st.rerun()

# ---- Chat ------------------------------------------------------------------
for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        if m["role"] == "assistant":
            render_assistant(m)
        else:
            st.markdown(m["content"])

if question := st.chat_input("Ask something about your documents"):
    history = [
        {"role": m["role"], "content": m["content"]} for m in st.session_state.messages[-6:]
    ]
    st.session_state.messages.append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.markdown(question)

    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            try:
                r = requests.post(
                    f"{API}/chat", json={"question": question, "history": history}, timeout=120
                )
                r.raise_for_status()
                msg = {"role": "assistant", "content": r.json()["answer"], **r.json()}
                msg["content"] = r.json()["answer"]
            except requests.RequestException as e:
                msg = {"role": "assistant", "content": f"Request failed: {e}", "question_type": "error"}
        render_assistant(msg)
    st.session_state.messages.append(msg)
