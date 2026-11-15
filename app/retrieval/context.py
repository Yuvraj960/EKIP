"""app.retrieval.context — Context formatter and citation extractor.

Transforms retrieved Document chunks into numbered evidence blocks for LLM prompts
and extracts structured Citation models for API responses.

Usage:
    from app.retrieval.context import format_context, extract_citations
    context_str = format_context(chunks)
    citations = extract_citations(chunks)
"""

from langchain_core.documents import Document
from langsmith import traceable

from app.api.schemas import Citation
from app.core.tracing import (
    META_CITATIONS_COUNT,
    META_MODULE,
    RUN_TYPE_PARSER,
    RUN_TYPE_PROMPT,
    TAG_EKIP,
    add_trace_metadata,
)

NO_EVIDENCE_TEXT: str = "No relevant evidence found."
MAX_CONTEXT_LENGTH: int = 8000
DEFAULT_EXCERPT_LENGTH: int = 200
DEFAULT_SOURCE: str = "unknown_source"
DEFAULT_SECTION: str = "General"


@traceable(
    name="2.2 Context Assembly",
    run_type=RUN_TYPE_PROMPT,
    tags=[TAG_EKIP, "context", "prompt"],
    metadata={META_MODULE: "app.retrieval.context", "step": "2.2_context"},
)
def format_context(
    chunks: list[Document],
    max_length: int = MAX_CONTEXT_LENGTH,
) -> str:
    """Format retrieved document chunks into numbered evidence blocks for the LLM.

    Args:
        chunks: List of Document chunks from the retriever.
        max_length: Maximum character length for total formatted context.

    Returns:
        Formatted context string containing numbered blocks with source and section.
    """
    if not chunks:
        return NO_EVIDENCE_TEXT

    blocks: list[str] = []
    current_length = 0

    for idx, chunk in enumerate(chunks, start=1):
        source = chunk.metadata.get("source", DEFAULT_SOURCE)
        section = chunk.metadata.get("section", DEFAULT_SECTION)
        body = chunk.page_content.strip()

        block = f"[{idx}] SOURCE: {source} | SECTION: {section}\n{body}"
        block_length = len(block) + 2  # account for newline separation

        if current_length + block_length > max_length:
            break

        blocks.append(block)
        current_length += block_length

    result = "\n\n".join(blocks) if blocks else NO_EVIDENCE_TEXT
    add_trace_metadata({"chunks_formatted": len(blocks), "total_chars": len(result)})
    return result


@traceable(
    name="2.4 Citation Extraction",
    run_type=RUN_TYPE_PARSER,
    tags=[TAG_EKIP, "citations", "parser"],
    metadata={META_MODULE: "app.retrieval.context", "step": "2.4_citations"},
)
def extract_citations(
    chunks: list[Document],
    max_excerpt_len: int = DEFAULT_EXCERPT_LENGTH,
) -> list[Citation]:
    """Extract Citation models from retrieved Document chunks.

    Args:
        chunks: List of Document chunks with metadata.
        max_excerpt_len: Maximum character length for passage excerpts.

    Returns:
        List of Citation objects with source, section, and passage excerpt.
    """
    citations: list[Citation] = []
    seen: set[tuple[str, str, str]] = set()

    for chunk in chunks:
        source = chunk.metadata.get("source", DEFAULT_SOURCE)
        section = chunk.metadata.get("section", DEFAULT_SECTION)
        raw_text = chunk.page_content.strip().replace("\n", " ")

        if len(raw_text) > max_excerpt_len:
            excerpt = f"{raw_text[:max_excerpt_len].rstrip()}..."
        else:
            excerpt = raw_text

        dedup_key = (source, section, excerpt[:50])
        if dedup_key in seen:
            continue
        seen.add(dedup_key)

        citations.append(
            Citation(
                source=source,
                section=section,
                passage_excerpt=excerpt,
            )
        )

    add_trace_metadata({META_CITATIONS_COUNT: len(citations)})
    return citations
