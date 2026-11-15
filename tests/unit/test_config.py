"""tests.unit.test_config — Unit tests for app.core.config."""

import pytest

from app.core.config import EngineType, Settings


def test_settings_default_values() -> None:
    """Verify that default settings conform to project specifications."""
    default_settings = Settings(_env_file=None)  # type: ignore[call-arg]
    assert default_settings.inference_engine == EngineType.HOSTED
    assert default_settings.embedding_engine == EngineType.HOSTED
    assert default_settings.inference_model == "gemini-3.1-flash-lite"
    assert default_settings.embedding_model == "models/gemini-embedding-001"
    assert default_settings.chat_model == "gemini-3.1-flash-lite"
    assert default_settings.embed_model == "models/gemini-embedding-001"
    assert default_settings.ollama_or_any_local_endpoint == "http://localhost:11434"
    assert default_settings.chroma_collection_name == "ekip_docs"
    assert default_settings.chunk_size == 1000
    assert default_settings.chunk_overlap == 200
    assert default_settings.retrieval_top_k == 5
    assert default_settings.langsmith_project == "ekip"


def test_settings_instantiation() -> None:
    """Verify that Settings can be instantiated with custom values."""
    custom_settings = Settings(
        _env_file=None,  # type: ignore[call-arg]
        gemini_api_key="custom-test-key",
        chunk_size=500,
        chunk_overlap=50,
    )
    assert custom_settings.gemini_api_key == "custom-test-key"
    assert custom_settings.google_api_key == "custom-test-key"
    assert custom_settings.chunk_size == 500
    assert custom_settings.chunk_overlap == 50


def test_settings_local_engine_configuration() -> None:
    """Verify that LOCAL engines configure properly via parameters."""
    local_settings = Settings(
        _env_file=None,  # type: ignore[call-arg]
        inference_engine=EngineType.LOCAL,
        embedding_engine=EngineType.LOCAL,
        inference_model="llama3.2:3b",
        embedding_model="nomic-embed-text",
        ollama_or_any_local_endpoint="http://127.0.0.1:11434",
    )
    assert local_settings.inference_engine == EngineType.LOCAL
    assert local_settings.embedding_engine == EngineType.LOCAL
    assert local_settings.inference_model == "llama3.2:3b"
    assert local_settings.chat_model == "llama3.2:3b"
    assert local_settings.embedding_model == "nomic-embed-text"
    assert local_settings.embed_model == "nomic-embed-text"
    assert local_settings.ollama_or_any_local_endpoint == "http://127.0.0.1:11434"


def test_settings_env_model_override(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify that environment variables control engines and models."""
    monkeypatch.setenv("INFERENCE_ENGINE", "LOCAL")
    monkeypatch.setenv("INFERENCE_MODEL", "qwen2.5:3b")
    monkeypatch.setenv("EMBEDDING_ENGINE", "LOCAL")
    monkeypatch.setenv("EMBEDDING_MODEL", "bge-small-en-v1.5")

    custom_settings = Settings(_env_file=None)  # type: ignore[call-arg]
    assert custom_settings.inference_engine == EngineType.LOCAL
    assert custom_settings.inference_model == "qwen2.5:3b"
    assert custom_settings.embedding_engine == EngineType.LOCAL
    assert custom_settings.embedding_model == "bge-small-en-v1.5"
