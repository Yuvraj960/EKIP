"""tests.unit.test_indexer — Unit tests for app.ingestion.indexer."""

import uuid

import pytest
from langchain_community.vectorstores import Chroma
from langchain_core.documents import Document
from langchain_core.embeddings import FakeEmbeddings
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_ollama import OllamaEmbeddings

from app.core.config import EngineType, settings
from app.ingestion.indexer import (
    delete_existing_source,
    get_embedding_model,
    index_documents,
)


@pytest.fixture
def fake_vector_store() -> Chroma:
    """Provide an isolated in-memory Chroma instance with deterministic fake embeddings."""
    return Chroma(
        collection_name=f"test_{uuid.uuid4().hex}",
        embedding_function=FakeEmbeddings(size=16),
    )


def test_index_empty_documents_list(fake_vector_store: Chroma) -> None:
    """Verify that passing an empty list returns 0 and leaves store empty."""
    indexed_count = index_documents([], store=fake_vector_store)
    assert indexed_count == 0
    assert len(fake_vector_store.get()["ids"]) == 0


def test_index_documents_stores_metadata(
    fake_vector_store: Chroma,
    sample_chunks: list[Document],
) -> None:
    """Verify that chunks are indexed with their metadata and IDs."""
    indexed_count = index_documents(sample_chunks, store=fake_vector_store)
    assert indexed_count == len(sample_chunks)

    stored = fake_vector_store.get()
    assert len(stored["ids"]) == 2
    assert "auth_guide_001" in stored["ids"]
    assert "auth_guide_002" in stored["ids"]


def test_reindexing_prevents_duplicate_chunks(fake_vector_store: Chroma) -> None:
    """Verify that indexing the same document source replaces old chunks."""
    v1_chunks = [
        Document(
            page_content="V1 content first paragraph",
            metadata={"source": "guide.md", "chunk_id": "guide_001"},
        ),
        Document(
            page_content="V1 content second paragraph",
            metadata={"source": "guide.md", "chunk_id": "guide_002"},
        ),
    ]
    index_documents(v1_chunks, store=fake_vector_store)
    assert len(fake_vector_store.get()["ids"]) == 2

    v2_chunks = [
        Document(
            page_content="V2 completely revised content",
            metadata={"source": "guide.md", "chunk_id": "guide_001"},
        ),
    ]
    index_documents(v2_chunks, store=fake_vector_store)

    stored = fake_vector_store.get()
    assert len(stored["ids"]) == 1
    assert stored["documents"][0] == "V2 completely revised content"


def test_delete_existing_source_preserves_other_sources(
    fake_vector_store: Chroma,
) -> None:
    """Verify delete_existing_source only removes matching records."""
    chunks = [
        Document(page_content="A", metadata={"source": "a.md", "chunk_id": "a_001"}),
        Document(page_content="B", metadata={"source": "b.md", "chunk_id": "b_001"}),
    ]
    index_documents(chunks, store=fake_vector_store)

    deleted_count = delete_existing_source(fake_vector_store, "a.md")
    assert deleted_count == 1

    remaining = fake_vector_store.get()
    assert len(remaining["ids"]) == 1
    assert remaining["metadatas"][0]["source"] == "b.md"


def test_get_embedding_model_hosted(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify that get_embedding_model returns GoogleGenerativeAIEmbeddings under HOSTED."""
    monkeypatch.setattr(settings, "embedding_engine", EngineType.HOSTED)
    emb = get_embedding_model()
    assert isinstance(emb, GoogleGenerativeAIEmbeddings)


def test_get_embedding_model_local(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify that get_embedding_model returns OllamaEmbeddings under LOCAL engine."""
    monkeypatch.setattr(settings, "embedding_engine", EngineType.LOCAL)
    monkeypatch.setattr(settings, "embedding_model", "nomic-embed-text")
    monkeypatch.setattr(settings, "ollama_or_any_local_endpoint", "http://localhost:11434")

    emb = get_embedding_model()
    assert isinstance(emb, OllamaEmbeddings)
    assert emb.model == "nomic-embed-text"
    assert emb.base_url == "http://localhost:11434"

