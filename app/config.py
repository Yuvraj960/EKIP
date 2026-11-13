"""Central application settings (env / .env driven)."""
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    google_api_key: str
    chat_model: str = "gemini-2.5-flash-lite"
    embedding_model: str = "models/gemini-embedding-001"

    chroma_dir: Path = Path("data/chroma")  # Chroma persists to SQLite here
    upload_dir: Path = Path("data/uploads")
    collection_name: str = "documents"

    chunk_size: int = 1000
    chunk_overlap: int = 150
    top_k: int = 4


@lru_cache
def get_settings() -> Settings:
    return Settings()
