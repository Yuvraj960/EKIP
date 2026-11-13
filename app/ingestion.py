"""Load -> split -> attach metadata -> embed into Chroma."""
import hashlib
from collections import defaultdict
from pathlib import Path

from langchain_community.document_loaders import Docx2txtLoader, PyPDFLoader, TextLoader
from langchain_core.documents import Document
from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter

from app.config import get_settings
from app.models import get_vectorstore

SUPPORTED = {".pdf", ".txt", ".md", ".docx"}


def load_file(path: Path) -> list[Document]:
    ext = path.suffix.lower()
    if ext not in SUPPORTED:
        raise ValueError(f"Unsupported file type: {ext}")
    if ext == ".pdf":
        return PyPDFLoader(str(path)).load()
    if ext == ".docx":
        return Docx2txtLoader(str(path)).load()
    return TextLoader(str(path), encoding="utf-8").load()


def split_documents(docs: list[Document], ext: str) -> list[Document]:
    s = get_settings()
    if ext == ".md":  # keep heading structure as section metadata
        md = MarkdownHeaderTextSplitter([("#", "h1"), ("##", "h2"), ("###", "h3")])
        sections = []
        for d in docs:
            for part in md.split_text(d.page_content):
                part.metadata = {**d.metadata, **part.metadata}
                sections.append(part)
        docs = sections
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=s.chunk_size, chunk_overlap=s.chunk_overlap
    )
    return splitter.split_documents(docs)


def _section(meta: dict, ext: str) -> str:
    if ext == ".pdf":
        return f"page {int(meta.get('page', 0)) + 1}"
    if ext == ".md":
        heads = [meta[k] for k in ("h1", "h2", "h3") if meta.get(k)]
        return " > ".join(heads) or "Introduction"
    return "full text"


def ingest_file(path: Path) -> dict:
    ext = path.suffix.lower()
    version = hashlib.sha256(path.read_bytes()).hexdigest()[:8]
    title = path.stem.replace("_", " ").replace("-", " ").title()

    chunks = split_documents(load_file(path), ext)
    chunks = [c for c in chunks if c.page_content.strip()]
    if not chunks:
        raise ValueError("No extractable text found (scanned PDF?)")

    for i, c in enumerate(chunks):
        c.metadata = {
            "source": path.name,
            "title": title,
            "section": _section(c.metadata, ext),
            "doc_version": version,
            "chunk_id": f"{path.stem}-{version}-{i}",
        }

    vs = get_vectorstore()
    old = vs.get(where={"source": path.name})["ids"]  # re-upload replaces old version
    if old:
        vs.delete(ids=old)
    vs.add_documents(chunks, ids=[c.metadata["chunk_id"] for c in chunks])
    return {"source": path.name, "version": version, "chunks": len(chunks)}


def list_documents() -> list[dict]:
    metas = get_vectorstore().get(include=["metadatas"])["metadatas"]
    agg: dict[str, dict] = defaultdict(lambda: {"chunks": 0})
    for m in metas:
        d = agg[m["source"]]
        d["chunks"] += 1
        d["version"] = m["doc_version"]
    return [{"source": k, **v} for k, v in sorted(agg.items())]
