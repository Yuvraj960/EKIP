"""LangChain chat model, embedding model and vector store factories."""
from functools import lru_cache

from langchain_chroma import Chroma
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings

from app.config import get_settings


@lru_cache
def get_chat_model() -> ChatGoogleGenerativeAI:
    s = get_settings()
    return ChatGoogleGenerativeAI(
        model=s.chat_model, temperature=0, google_api_key=s.google_api_key
    )


@lru_cache
def get_embeddings() -> GoogleGenerativeAIEmbeddings:
    s = get_settings()
    return GoogleGenerativeAIEmbeddings(
        model=s.embedding_model, google_api_key=s.google_api_key
    )


@lru_cache
def get_vectorstore() -> Chroma:
    s = get_settings()
    s.chroma_dir.mkdir(parents=True, exist_ok=True)
    return Chroma(
        collection_name=s.collection_name,
        embedding_function=get_embeddings(),
        persist_directory=str(s.chroma_dir),
    )
