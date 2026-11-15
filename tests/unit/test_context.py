"""tests.unit.test_context — Unit tests for app.retrieval.context."""

from langchain_core.documents import Document

from app.retrieval.context import (
    NO_EVIDENCE_TEXT,
    extract_citations,
    format_context,
)


def test_format_context_empty_list() -> None:
    """Verify that an empty chunk list returns the fallback evidence text."""
    assert format_context([]) == NO_EVIDENCE_TEXT


def test_format_context_numbered_blocks(sample_chunks: list[Document]) -> None:
    """Verify that chunks are formatted with [1], [2] headers and metadata."""
    formatted = format_context(sample_chunks)
    assert "[1] SOURCE: auth_guide.md | SECTION: OAuth2 Flow" in formatted
    assert "[2] SOURCE: auth_guide.md | SECTION: Token Specifications" in formatted
    assert "The token is validated" in formatted
    assert "Refresh tokens have a 30-day" in formatted


def test_format_context_max_length_limit(sample_chunks: list[Document]) -> None:
    """Verify context stops appending when max_length is reached."""
    formatted = format_context(sample_chunks, max_length=150)
    assert "[1] SOURCE: auth_guide.md" in formatted
    assert "[2] SOURCE: auth_guide.md" not in formatted


def test_extract_citations_structure(sample_chunks: list[Document]) -> None:
    """Verify that Citation objects are correctly extracted with fields."""
    citations = extract_citations(sample_chunks)
    assert len(citations) == 2
    assert citations[0].source == "auth_guide.md"
    assert citations[0].section == "OAuth2 Flow"
    assert citations[0].passage_excerpt.startswith("The token is validated")
    assert citations[1].source == "auth_guide.md"
    assert citations[1].section == "Token Specifications"


def test_extract_citations_truncates_long_passages() -> None:
    """Verify passages longer than max_excerpt_len are truncated with ellipsis."""
    long_doc = Document(
        page_content="a" * 300,
        metadata={"source": "doc.md", "section": "Sec"},
    )
    citations = extract_citations([long_doc], max_excerpt_len=50)
    assert len(citations) == 1
    assert citations[0].passage_excerpt.endswith("...")
    assert len(citations[0].passage_excerpt) <= 55


def test_extract_citations_deduplicates_identical_chunks() -> None:
    """Verify identical duplicate chunks do not produce duplicate citations."""
    dup_doc = Document(
        page_content="Same exact content",
        metadata={"source": "same.md", "section": "Same"},
    )
    citations = extract_citations([dup_doc, dup_doc])
    assert len(citations) == 1
