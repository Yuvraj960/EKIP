"""app.core.llm — Centralized LLM factory and instance provider.

Constructs configured BaseChatModel instances based on application settings.
Supports both HOSTED (Google Gemini) and LOCAL (Ollama / Local OpenAI-compatible)
inference engines dynamically configured via INFERENCE_ENGINE in .env.

Usage:
    from app.core.llm import get_chat_llm
    llm = get_chat_llm()
"""

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_ollama import ChatOllama

from app.core.config import EngineType, settings


def get_chat_llm(
    model: str | None = None,
    temperature: float = 0.0,
) -> BaseChatModel:
    """Return a configured chat model instance based on active inference engine.

    Args:
        model: Optional model name override. Defaults to settings.inference_model.
        temperature: Sampling temperature for generation. Defaults to 0.0.

    Returns:
        Configured BaseChatModel instance (ChatGoogleGenerativeAI or ChatOllama).
    """
    resolved_model = model if model is not None else settings.inference_model
    if settings.inference_engine == EngineType.LOCAL:
        return ChatOllama(
            model=resolved_model,
            base_url=settings.ollama_or_any_local_endpoint,
            temperature=temperature,
        )

    return ChatGoogleGenerativeAI(
        model=resolved_model,
        google_api_key=settings.gemini_api_key,  # type: ignore[call-arg]
        temperature=temperature,
    )
