"""app.core.config — Application settings and configuration.

Loads all configuration values from environment variables or .env file using
Pydantic BaseSettings. Enforces typed access to all project settings and
supports both HOSTED and LOCAL inference/embedding engines.

Usage:
    from app.core.config import settings
    print(settings.inference_model)
"""

from enum import StrEnum
from typing import Any

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class EngineType(StrEnum):
    """Engine backend type for LLM inference or embedding computations."""

    HOSTED = "HOSTED"
    LOCAL = "LOCAL"


def _resolve_api_key(data: dict[str, Any]) -> str:
    """Extract primary or fallback API key from settings data."""
    gemini_key = data.get("gemini_api_key") or data.get("GEMINI_API_KEY")
    google_key = data.get("google_api_key") or data.get("GOOGLE_API_KEY")
    return str(gemini_key or google_key or "")


def _resolve_model(data: dict[str, Any], primary: str, legacy: str, default: str) -> str:
    """Extract model name with fallback to legacy key and default value."""
    val = (
        data.get(primary.lower())
        or data.get(primary.upper())
        or data.get(legacy.lower())
        or data.get(legacy.upper())
    )
    return str(val or default)


def _resolve_engine(data: dict[str, Any], key: str) -> str:
    """Normalize engine string to uppercase EngineType value."""
    val = data.get(key.lower()) or data.get(key.upper())
    return str(val).strip().upper() if val else EngineType.HOSTED.value


class Settings(BaseSettings):
    """Application settings loaded from environment variables and .env file.

    Attributes:
        gemini_api_key: Primary API key for Google Gemini model access.
        google_api_key: Backward-compatible alias for Gemini API key.
        ollama_or_any_local_endpoint: Base URL for local Ollama/OpenAI API endpoint.
        inference_engine: Engine type for text generation (HOSTED or LOCAL).
        embedding_engine: Engine type for vector embeddings (HOSTED or LOCAL).
        inference_model: Model identifier used for chat/answer generation.
        embedding_model: Model identifier used for vector embeddings.
        chat_model: Backward-compatible alias for inference_model.
        embed_model: Backward-compatible alias for embedding_model.
        langsmith_api_key: API key for LangSmith tracing and evaluation.
        langsmith_project: Project name in LangSmith.
        langsmith_tracing: Whether LangSmith tracing is enabled.
        langsmith_tracing_v2: Whether LangSmith v2 tracing is enabled.
        langsmith_endpoint: LangSmith API endpoint URL.
        chroma_persist_dir: Local directory where ChromaDB stores index data.
        chroma_collection_name: Name of the ChromaDB collection for documents.
        retrieval_top_k: Number of chunks retrieved during similarity search.
        retrieval_min_score: Minimum similarity score threshold for chunks.
        chunk_size: Target size in characters for document chunks.
        chunk_overlap: Overlap in characters between adjacent chunks.
        api_host: Host interface for FastAPI server.
        api_port: Port number for FastAPI server.
        log_level: Logging severity level (e.g. INFO, DEBUG).
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    gemini_api_key: str = ""
    google_api_key: str = ""
    ollama_or_any_local_endpoint: str = "http://localhost:11434"
    inference_engine: EngineType = EngineType.HOSTED
    embedding_engine: EngineType = EngineType.HOSTED
    inference_model: str = "gemini-3.1-flash-lite"
    embedding_model: str = "models/gemini-embedding-001"
    chat_model: str = ""
    embed_model: str = ""

    langsmith_api_key: str = ""
    langsmith_project: str = "ekip"
    langsmith_tracing: bool = True
    langsmith_tracing_v2: bool = True
    langsmith_endpoint: str = "https://api.smith.langchain.com"
    chroma_persist_dir: str = "./data/chroma_db"
    chroma_collection_name: str = "ekip_docs"
    retrieval_top_k: int = 5
    retrieval_min_score: float = 0.35
    chunk_size: int = 1000
    chunk_overlap: int = 200
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    log_level: str = "INFO"

    @model_validator(mode="before")
    @classmethod
    def _harmonize_settings(cls, data: Any) -> Any:
        """Harmonize user-specified environment variables and legacy aliases.

        Args:
            data: Raw input dictionary from environment or keyword arguments.

        Returns:
            Normalized dictionary matching Settings field definitions.
        """
        if not isinstance(data, dict):
            return data

        key = _resolve_api_key(data)
        data["gemini_api_key"] = key
        data["google_api_key"] = key

        inf = _resolve_model(data, "inference_model", "chat_model", "gemini-3.1-flash-lite")
        data["inference_model"] = inf
        data["chat_model"] = inf

        emb = _resolve_model(data, "embedding_model", "embed_model", "models/gemini-embedding-001")
        data["embedding_model"] = emb
        data["embed_model"] = emb

        data["inference_engine"] = _resolve_engine(data, "inference_engine")
        data["embedding_engine"] = _resolve_engine(data, "embedding_engine")

        return data


settings = Settings()
