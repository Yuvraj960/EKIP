"""tests.unit.test_chunker — Unit tests for app.ingestion.chunker."""

from langchain_core.documents import Document

from app.ingestion.chunker import (
    chunk_documents,
    extract_section,
    extract_title,
)


def test_short_doc_produces_at_least_one_chunk(sample_document: Document) -> None:
    """Verify that a short document produces at least one chunk."""
    chunks = chunk_documents([sample_document])
    assert len(chunks) >= 1
    assert "The token is validated" in chunks[0].page_content


def test_long_doc_produces_multiple_chunks(sample_long_document: Document) -> None:
    """Verify that a document exceeding chunk size produces multiple chunks."""
    chunks = chunk_documents([sample_long_document], chunk_size=300, chunk_overlap=50)
    assert len(chunks) > 1


def test_all_chunks_have_required_metadata(sample_long_document: Document) -> None:
    """Verify every chunk has source, title, section, and chunk_id in metadata."""
    chunks = chunk_documents([sample_long_document], chunk_size=300, chunk_overlap=50)
    for chunk in chunks:
        assert "source" in chunk.metadata
        assert "title" in chunk.metadata
        assert "section" in chunk.metadata
        assert "chunk_id" in chunk.metadata
        assert chunk.metadata["source"] == "system_architecture.md"
        assert chunk.metadata["title"] == "System Architecture"


def test_chunk_ids_are_unique(sample_long_document: Document) -> None:
    """Verify chunk_id values are strictly unique across chunks."""
    chunks = chunk_documents([sample_long_document], chunk_size=200, chunk_overlap=30)
    chunk_ids = [c.metadata["chunk_id"] for c in chunks]
    assert len(chunk_ids) == len(set(chunk_ids))
    assert all(cid.startswith("system_architecture_") for cid in chunk_ids)


def test_chunk_size_bounds(sample_long_document: Document) -> None:
    """Verify chunk text length does not exceed chunk_size + chunk_overlap."""
    chunk_size = 250
    chunk_overlap = 50
    chunks = chunk_documents(
        [sample_long_document],
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
    )
    max_allowed = chunk_size + chunk_overlap
    for chunk in chunks:
        assert len(chunk.page_content) <= max_allowed


def test_extract_title_from_heading() -> None:
    """Verify title is parsed from the first level-1 markdown heading."""
    doc = Document(page_content="# Deployment Playbook\n\nSteps here.", metadata={})
    assert extract_title(doc) == "Deployment Playbook"


def test_extract_title_fallback_to_source() -> None:
    """Verify title falls back to humanized filename if no h1 is present."""
    doc = Document(page_content="No heading content", metadata={"source": "api_reference.md"})
    assert extract_title(doc) == "Api Reference"


def test_extract_section_nearest_heading() -> None:
    """Verify extract_section picks the nearest heading above cursor position."""
    text = "# Title\n\n## Section One\nText 1\n\n## Section Two\nText 2"
    assert extract_section(text, position=0) == "Title"
    assert extract_section(text, position=25) == "Section One"
    assert extract_section(text, position=55) == "Section Two"


def test_empty_document_produces_no_chunks() -> None:
    """Verify that empty or whitespace-only documents produce zero chunks."""
    empty_doc = Document(page_content="   \n\n   ", metadata={"source": "empty.md"})
    chunks = chunk_documents([empty_doc])
    assert chunks == []
