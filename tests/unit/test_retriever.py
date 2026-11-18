"""tests.unit.test_retriever — Unit tests for app.retrieval.retriever."""

from unittest.mock import MagicMock

from langchain_community.vectorstores import Chroma
from langchain_core.documents import Document

from app.retrieval.retriever import retrieve_chunks


def test_retrieve_empty_query_returns_empty_list() -> None:
    """Verify that an empty or whitespace-only query returns an empty list."""
    assert retrieve_chunks("") == []
    assert retrieve_chunks("   \n\t  ") == []


def test_retrieve_chunks_filters_by_min_score() -> None:
    """Verify that candidates below min_score are excluded."""
    high_doc = Document(page_content="High match", metadata={"source": "a.md"})
    low_doc = Document(page_content="Low match", metadata={"source": "b.md"})

    mock_store = MagicMock(spec=Chroma)
    mock_store.similarity_search_with_relevance_scores.return_value = [
        (high_doc, 0.85),
        (low_doc, 0.20),
    ]

    results = retrieve_chunks(
        "test query",
        top_k=5,
        min_score=0.5,
        store=mock_store,
    )

    assert len(results) == 1
    assert results[0].page_content == "High match"
    assert results[0].metadata["score"] == 0.85


def test_retrieve_chunks_all_filtered_when_scores_low() -> None:
    """Verify that an empty list is returned if no candidate passes threshold."""
    doc = Document(page_content="Weak match", metadata={"source": "a.md"})

    mock_store = MagicMock(spec=Chroma)
    mock_store.similarity_search_with_relevance_scores.return_value = [(doc, 0.15)]

    results = retrieve_chunks(
        "pizza question",
        top_k=5,
        min_score=0.3,
        store=mock_store,
    )

    assert results == []


def test_retrieve_chunks_passes_top_k() -> None:
    """Verify that custom top_k argument is forwarded to store search."""
    mock_store = MagicMock(spec=Chroma)
    mock_store.similarity_search_with_relevance_scores.return_value = []

    retrieve_chunks("test", top_k=7, store=mock_store)

    mock_store.similarity_search_with_relevance_scores.assert_called_once_with(
        "test",
        k=7,
    )


def test_retrieve_chunks_multi_subdatabase(tmp_path: MagicMock) -> None:
    """Verify aggregation across partitioned sub-database directories."""
    from unittest.mock import patch

    doc_a = Document(page_content="Archive A", metadata={"source": "a.md"})
    doc_b = Document(page_content="Archive B", metadata={"source": "b.md"})

    store_a = MagicMock(spec=Chroma)
    store_a.similarity_search_with_relevance_scores.return_value = [(doc_a, 0.90)]

    store_b = MagicMock(spec=Chroma)
    store_b.similarity_search_with_relevance_scores.return_value = [(doc_b, 0.75)]

    def mock_get_store(
        persist_dir: str | None = None,
        collection_name: str | None = None,
    ) -> Chroma:
        if collection_name == "db1":
            return store_a
        return store_b

    with (
        patch(
            "app.retrieval.retriever._get_sub_database_paths",
            return_value=[tmp_path / "db1", tmp_path / "db2"],
        ),
        patch("app.retrieval.retriever.get_vector_store", side_effect=mock_get_store),
    ):
        results = retrieve_chunks("multi-query", top_k=5, min_score=0.5)

    assert len(results) == 2
    assert results[0].page_content == "Archive A"
    assert results[0].metadata["score"] == 0.90
    assert results[1].page_content == "Archive B"
    assert results[1].metadata["score"] == 0.75
