"""app.ingestion.run_ingest — CLI entry point for document ingestion.

Loads engineering documents from a folder, chunks them with metadata,
and indexes them into the ChromaDB vector store.

Usage:
    python -m app.ingestion.run_ingest data/sample_docs/
"""

import sys
from pathlib import Path

from langsmith import traceable

from app.core.tracing import (
    META_CHUNKS_COUNT,
    META_LAYER,
    META_MODULE,
    RUN_TYPE_CHAIN,
    TAG_EKIP,
    TAG_INGESTION,
    add_trace_metadata,
    add_trace_tags,
)
from app.ingestion.chunker import chunk_documents
from app.ingestion.indexer import get_vector_store, index_documents
from app.ingestion.loaders import load_documents


@traceable(
    name="ingestion.run_pipeline",
    run_type=RUN_TYPE_CHAIN,
    tags=[TAG_EKIP, TAG_INGESTION, "pipeline"],
    metadata={META_MODULE: "app.ingestion.run_ingest", META_LAYER: "ingestion"},
)
def run_ingestion_pipeline(
    folder_path: Path,
    persist_dir: str | None = None,
    collection_name: str | None = None,
    archive_name: str | None = None,
) -> tuple[int, int]:
    """Execute the full ingestion pipeline: load, chunk, and index.

    Args:
        folder_path: Directory path containing documents to index.
        persist_dir: Optional Chroma persistence directory override.
        collection_name: Optional Chroma collection name override.
        archive_name: Optional archive name to enrich chunk metadata.

    Returns:
        Tuple of (loaded_documents_count, indexed_chunks_count).

    Raises:
        NotADirectoryError: If folder_path does not exist or is not a directory.
    """
    if not folder_path.is_dir():
        raise NotADirectoryError(f"Directory not found: {folder_path}")

    docs = load_documents(folder_path)
    if not docs:
        return 0, 0

    chunks = chunk_documents(docs)
    if archive_name:
        for chunk in chunks:
            chunk.metadata["archive_name"] = archive_name

    store = (
        get_vector_store(persist_dir=persist_dir, collection_name=collection_name)
        if (persist_dir or collection_name)
        else None
    )
    indexed_count = index_documents(chunks, store=store)

    add_trace_tags([f"docs:{len(docs)}", f"chunks:{indexed_count}"])
    add_trace_metadata(
        {
            "docs_count": len(docs),
            META_CHUNKS_COUNT: indexed_count,
            "folder": str(folder_path),
            "archive": archive_name or "",
        }
    )
    return len(docs), indexed_count


def main() -> None:
    """CLI entry point for document ingestion."""
    target_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("data/sample_docs")
    print(f"Starting ingestion from: {target_dir}")

    doc_count, chunk_count = run_ingestion_pipeline(target_dir)
    print(f"Successfully indexed {chunk_count} chunks from {doc_count} documents.")


if __name__ == "__main__":
    main()
