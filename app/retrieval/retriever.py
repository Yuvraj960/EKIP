"""app.retrieval.retriever — ChromaDB chunk retriever.

Queries partitioned ChromaDB sub-databases with an embedding of the user's question,
scores chunk relevance, and returns documents exceeding the minimum score threshold.

Usage:
    from app.retrieval.retriever import retrieve_chunks
    chunks = retrieve_chunks("authentication flow")
"""

from pathlib import Path

from langchain_community.vectorstores import Chroma
from langchain_core.documents import Document
from langsmith import traceable

from app.core.config import settings
from app.core.tracing import (
    META_CHUNKS_COUNT,
    META_LAYER,
    META_MODULE,
    RUN_TYPE_RETRIEVER,
    TAG_EKIP,
    TAG_RETRIEVER,
    add_trace_metadata,
    add_trace_tags,
)
from app.ingestion.archive_manager import CHROMA_SQLITE_FILE
from app.ingestion.indexer import get_vector_store


def _get_sub_database_paths(root: Path) -> list[Path]:
    """Return all existing Chroma sub-database directories containing chroma.sqlite3.

    Args:
        root: Root directory of Chroma persistence.

    Returns:
        List of Path objects for active sub-database directories.
    """
    if not root.exists():
        return []
    return [d for d in root.iterdir() if d.is_dir() and (d / CHROMA_SQLITE_FILE).exists()]


def _query_candidates(
    clean_query: str,
    limit: int,
    store: Chroma | None,
) -> list[tuple[Document, float]]:
    """Query either provided store, active sub-databases, or fallback store.

    Args:
        clean_query: Stripped question string.
        limit: Candidate retrieval limit per store.
        store: Optional explicitly provided Chroma store instance.

    Returns:
        Aggregated list of (Document, score) tuples sorted by score descending.
    """
    if store is not None:
        return store.similarity_search_with_relevance_scores(clean_query, k=limit)

    root = Path(settings.chroma_persist_dir)
    sub_dbs = _get_sub_database_paths(root)
    if sub_dbs:
        aggregated: list[tuple[Document, float]] = []
        for sub_db in sub_dbs:
            sub_store = get_vector_store(persist_dir=str(sub_db), collection_name=sub_db.name)
            aggregated.extend(
                sub_store.similarity_search_with_relevance_scores(clean_query, k=limit)
            )
        aggregated.sort(key=lambda item: item[1], reverse=True)
        return aggregated

    default_store = get_vector_store()
    return default_store.similarity_search_with_relevance_scores(clean_query, k=limit)


@traceable(
    name="2.1 Document Retrieval (ChromaDB)",
    run_type=RUN_TYPE_RETRIEVER,
    tags=[TAG_EKIP, TAG_RETRIEVER],
    metadata={
        META_MODULE: "app.retrieval.retriever",
        META_LAYER: "retrieval",
        "step": "2.1_retrieval",
    },
)
def retrieve_chunks(
    query: str,
    top_k: int | None = None,
    min_score: float | None = None,
    store: Chroma | None = None,
) -> list[Document]:
    """Retrieve relevant chunks from ChromaDB filtered by minimum similarity score.

    Args:
        query: User's question or search query.
        top_k: Number of candidate chunks to retrieve. Defaults to config value.
        min_score: Minimum relevance score threshold (0.0 to 1.0). Defaults to config.
        store: Optional Chroma vector store instance. Defaults to configured store.

    Returns:
        List of Document objects passing the minimum relevance score threshold.
    """
    clean_query = query.strip()
    if not clean_query:
        return []

    limit = top_k if top_k is not None else settings.retrieval_top_k
    threshold = min_score if min_score is not None else settings.retrieval_min_score

    candidates = _query_candidates(clean_query, limit, store)

    filtered_chunks: list[Document] = []
    for doc, score in candidates:
        if score >= threshold:
            enriched_metadata = dict(doc.metadata)
            enriched_metadata["score"] = round(float(score), 4)
            filtered_chunks.append(
                Document(page_content=doc.page_content, metadata=enriched_metadata)
            )
        if len(filtered_chunks) >= limit:
            break

    add_trace_tags([f"chunks_found:{len(filtered_chunks)}"])
    add_trace_metadata(
        {
            META_CHUNKS_COUNT: len(filtered_chunks),
            "candidates_count": len(candidates),
            "min_score": threshold,
            "top_k": limit,
            "sources": list({c.metadata.get("source", "") for c in filtered_chunks}),
        }
    )
    return filtered_chunks
