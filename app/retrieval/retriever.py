"""app.retrieval.retriever — ChromaDB chunk retriever.

Queries the ChromaDB vector store with an embedding of the user's question,
scores chunk relevance, and returns documents exceeding the minimum score threshold.

Usage:
    from app.retrieval.retriever import retrieve_chunks
    chunks = retrieve_chunks("authentication flow")
"""

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
from app.ingestion.indexer import get_vector_store


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
    vector_store = store if store is not None else get_vector_store()

    candidates = vector_store.similarity_search_with_relevance_scores(
        clean_query,
        k=limit,
    )

    filtered_chunks: list[Document] = []
    for doc, score in candidates:
        if score >= threshold:
            enriched_metadata = dict(doc.metadata)
            enriched_metadata["score"] = round(float(score), 4)
            filtered_chunks.append(
                Document(page_content=doc.page_content, metadata=enriched_metadata)
            )

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
