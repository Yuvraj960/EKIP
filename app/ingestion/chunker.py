"""app.ingestion.chunker — Document text splitter and metadata attacher.

Splits loaded documents into smaller chunks for embedding and attaches
structured metadata (source, title, section, chunk_id).

Usage:
    from app.ingestion.chunker import chunk_documents
    chunks = chunk_documents(docs)
"""

import re
from pathlib import Path

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langsmith import traceable

from app.core.config import settings
from app.core.tracing import (
    META_CHUNKS_COUNT,
    META_MODULE,
    RUN_TYPE_CHAIN,
    TAG_EKIP,
    TAG_INGESTION,
    add_trace_metadata,
    add_trace_tags,
)

DEFAULT_TITLE: str = "Untitled Document"
DEFAULT_SECTION: str = "Overview"
HEADING_REGEX = re.compile(r"^(#{1,6})\s+(.+)$", re.MULTILINE)
TITLE_REGEX = re.compile(r"^#\s+(.+)$", re.MULTILINE)


def extract_title(doc: Document) -> str:
    """Extract document title from the first top-level heading or filename.

    Args:
        doc: Source Document object.

    Returns:
        Extracted or derived document title.
    """
    first_h1 = TITLE_REGEX.search(doc.page_content)
    if first_h1:
        return first_h1.group(1).strip()

    source = doc.metadata.get("source", "")
    if source:
        stem = Path(source).stem
        cleaned = stem.replace("_", " ").replace("-", " ")
        return cleaned.title()

    return DEFAULT_TITLE


def extract_section(
    text: str,
    position: int,
    default_section: str = DEFAULT_SECTION,
) -> str:
    """Find the nearest markdown heading at or above a character position.

    Args:
        text: Full document text.
        position: Character index where chunk begins.
        default_section: Fallback section name when no heading precedes position.

    Returns:
        Heading title of the nearest section.
    """
    headings = [m for m in HEADING_REGEX.finditer(text) if m.start() <= position + 5]
    if not headings:
        return default_section

    nearest_heading = headings[-1]
    return nearest_heading.group(2).strip()


def _generate_chunk_id(source_name: str, index: int) -> str:
    """Generate a deterministic, unique chunk ID.

    Args:
        source_name: Source file name.
        index: 1-based sequential index of the chunk.

    Returns:
        Unique chunk ID string, e.g. 'auth_guide_001'.
    """
    stem = Path(source_name).stem if source_name else "doc"
    clean_stem = re.sub(r"[^a-zA-Z0-9_]", "_", stem).strip("_").lower()
    prefix = clean_stem if clean_stem else "doc"
    return f"{prefix}_{index:03d}"


@traceable(
    name="ingestion.chunk_document",
    run_type=RUN_TYPE_CHAIN,
    tags=[TAG_EKIP, TAG_INGESTION, "chunk_doc"],
    metadata={META_MODULE: "app.ingestion.chunker"},
)
def chunk_document(
    doc: Document,
    text_splitter: RecursiveCharacterTextSplitter,
) -> list[Document]:
    """Split a single Document into chunks with enriched metadata.

    Args:
        doc: Source Document object.
        text_splitter: Configured RecursiveCharacterTextSplitter instance.

    Returns:
        List of chunk Document objects with source, title, section, and chunk_id.
    """
    if not doc.page_content.strip():
        return []

    title = extract_title(doc)
    source = doc.metadata.get("source", "")
    raw_chunks = text_splitter.split_text(doc.page_content)

    chunked_docs: list[Document] = []
    search_cursor = 0

    for idx, chunk_text in enumerate(raw_chunks, start=1):
        found_pos = doc.page_content.find(chunk_text[:50], search_cursor)
        pos = found_pos if found_pos != -1 else search_cursor
        search_cursor = pos

        section = extract_section(doc.page_content, pos)
        chunk_id = _generate_chunk_id(source, idx)

        metadata = dict(doc.metadata)
        metadata["source"] = source
        metadata["title"] = title
        metadata["section"] = section
        metadata["chunk_id"] = chunk_id

        chunked_docs.append(Document(page_content=chunk_text, metadata=metadata))

    return chunked_docs


@traceable(
    name="ingestion.chunk_documents",
    run_type=RUN_TYPE_CHAIN,
    tags=[TAG_EKIP, TAG_INGESTION, "chunker"],
    metadata={META_MODULE: "app.ingestion.chunker"},
)
def chunk_documents(
    docs: list[Document],
    chunk_size: int | None = None,
    chunk_overlap: int | None = None,
) -> list[Document]:
    """Split a list of documents into chunks with rich metadata.

    Args:
        docs: List of Document objects from loaders.
        chunk_size: Optional override for chunk size. Defaults to settings.chunk_size.
        chunk_overlap: Optional override for chunk overlap. Defaults to settings.chunk_overlap.

    Returns:
        List of all chunk Documents with source, title, section, and chunk_id.
    """
    size = chunk_size if chunk_size is not None else settings.chunk_size
    overlap = chunk_overlap if chunk_overlap is not None else settings.chunk_overlap

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=size,
        chunk_overlap=overlap,
        length_function=len,
    )

    all_chunks: list[Document] = []
    for doc in docs:
        all_chunks.extend(chunk_document(doc, splitter))

    add_trace_tags([f"chunks_produced:{len(all_chunks)}"])
    add_trace_metadata(
        {
            META_CHUNKS_COUNT: len(all_chunks),
            "docs_input": len(docs),
            "chunk_size": size,
            "chunk_overlap": overlap,
        }
    )
    return all_chunks
