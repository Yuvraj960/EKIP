"""tests.unit.conftest — Shared fixtures for unit tests."""

import pytest
from langchain_core.documents import Document


@pytest.fixture(autouse=True)
def disable_tracing_for_unit_tests(monkeypatch: pytest.MonkeyPatch) -> None:
    """Disable LangSmith remote tracing during unit test execution to keep projects clean."""
    monkeypatch.setenv("LANGSMITH_TRACING", "false")
    monkeypatch.setenv("LANGCHAIN_TRACING_V2", "false")


@pytest.fixture
def sample_document() -> Document:
    """A single Document for testing loaders and chunker."""
    return Document(
        page_content="# Auth Guide\n\n## OAuth2 Flow\n\nThe token is validated...",
        metadata={"source": "auth_guide.md"},
    )


@pytest.fixture
def sample_long_document() -> Document:
    """A multi-section long Document to test multi-chunk splitting."""
    sections = [
        "# System Architecture\n\nIntroduction to overall system design.\n\n",
        "## Ingestion Layer\n\n" + ("Data ingestion handles loading files and chunking. " * 30),
        "\n\n## Retrieval Layer\n\n" + ("Vector search retrieves top semantic matches. " * 30),
        "\n\n## Generation Layer\n\n" + ("LLM generates answers citing evidence. " * 30),
    ]
    return Document(
        page_content="".join(sections),
        metadata={"source": "system_architecture.md"},
    )


@pytest.fixture
def sample_chunks() -> list[Document]:
    """Pre-made chunks with full metadata for testing retrieval and context."""
    return [
        Document(
            page_content="The token is validated by checking the signature.",
            metadata={
                "source": "auth_guide.md",
                "title": "Auth Guide",
                "section": "OAuth2 Flow",
                "chunk_id": "auth_guide_001",
            },
        ),
        Document(
            page_content="Refresh tokens have a 30-day sliding expiration window.",
            metadata={
                "source": "auth_guide.md",
                "title": "Auth Guide",
                "section": "Token Specifications",
                "chunk_id": "auth_guide_002",
            },
        ),
    ]
