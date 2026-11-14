"""app.ingestion.indexer — Embed chunks and store in ChromaDB.

Takes document chunks (from chunker.py), embeds them using Gemini embeddings,
and stores them in a ChromaDB collection. Supports re-indexing by deleting
prior chunks matching the same source before writing new ones.

Usage:
    from app.ingestion.indexer import index_documents
    count = index_documents(chunks)
    print(f"Indexed {count} chunks.")
"""

from langchain_community.vectorstores import Chroma
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_ollama import OllamaEmbeddings
from langsmith import traceable

from app.core.config import EngineType, settings
from app.core.tracing import (
    META_CHUNKS_COUNT,
    META_MODULE,
    RUN_TYPE_CHAIN,
    TAG_EKIP,
    TAG_INGESTION,
    add_trace_metadata,
    add_trace_tags,
)


def get_embedding_model(model: str | None = None) -> Embeddings:
    """Instantiate and return configured embedding model based on EMBEDDING_ENGINE.

    Args:
        model: Optional model name override. Defaults to settings.embedding_model.

    Returns:
        Embeddings instance configured for LOCAL (Ollama) or HOSTED (Gemini) execution.
    """
    resolved_model = model if model is not None else settings.embedding_model
    if settings.embedding_engine == EngineType.LOCAL:
        return OllamaEmbeddings(
            model=resolved_model,
            base_url=settings.ollama_or_any_local_endpoint,
        )

    return GoogleGenerativeAIEmbeddings(
        model=resolved_model,
        google_api_key=settings.gemini_api_key,  # type: ignore[call-arg]
    )


def get_vector_store(
    embeddings: Embeddings | None = None,
    persist_dir: str | None = None,
    collection_name: str | None = None,
) -> Chroma:
    """Return a connected ChromaDB vector store instance.

    Args:
        embeddings: Optional embedding model instance.
        persist_dir: Optional persistence directory override.
        collection_name: Optional collection name override.

    Returns:
        Chroma vector store instance.
    """
    emb = embeddings if embeddings is not None else get_embedding_model()
    p_dir = persist_dir if persist_dir is not None else settings.chroma_persist_dir
    c_name = collection_name if collection_name is not None else settings.chroma_collection_name

    return Chroma(
        collection_name=c_name,
        persist_directory=p_dir,
        embedding_function=emb,
    )


def delete_existing_source(store: Chroma, source: str) -> int:
    """Delete all chunks with matching source metadata for clean re-indexing.

    Args:
        store: Target Chroma vector store instance.
        source: Filename source identifier to match.

    Returns:
        Number of chunk records deleted.
    """
    existing = store.get(where={"source": source})
    ids_to_delete = existing.get("ids", [])
    if ids_to_delete:
        store.delete(ids=ids_to_delete)
        return len(ids_to_delete)
    return 0


@traceable(
    name="ingestion.index_documents",
    run_type=RUN_TYPE_CHAIN,
    tags=[TAG_EKIP, TAG_INGESTION, "indexer", "chromadb"],
    metadata={META_MODULE: "app.ingestion.indexer"},
)
def index_documents(
    chunks: list[Document],
    store: Chroma | None = None,
) -> int:
    """Embed chunks and store them in ChromaDB with re-indexing deduplication.

    Args:
        chunks: List of chunk Document objects with metadata.
        store: Optional Chroma vector store instance.

    Returns:
        Number of chunks successfully indexed.
    """
    if not chunks:
        return 0

    vector_store = store if store is not None else get_vector_store()

    sources = {
        c.metadata["source"]
        for c in chunks
        if "source" in c.metadata and c.metadata["source"]
    }
    for source in sources:
        delete_existing_source(vector_store, source)

    ids = [c.metadata.get("chunk_id") for c in chunks]
    has_valid_ids = all(ids) and len(ids) == len(set(ids))

    if has_valid_ids:
        vector_store.add_documents(chunks, ids=ids)  # type: ignore[arg-type]
    else:
        vector_store.add_documents(chunks)

    add_trace_tags([f"indexed:{len(chunks)}"])
    add_trace_metadata(
        {
            META_CHUNKS_COUNT: len(chunks),
            "sources": list(sources),
        }
    )
    return len(chunks)
