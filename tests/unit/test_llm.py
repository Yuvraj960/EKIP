"""tests.unit.test_llm — Unit tests for app.core.llm."""

import pytest
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_ollama import ChatOllama

from app.core.config import EngineType, settings
from app.core.llm import get_chat_llm


def test_get_chat_llm_default_uses_settings_chat_model() -> None:
    """Verify that get_chat_llm defaults to settings.inference_model under HOSTED."""
    llm = get_chat_llm()
    assert isinstance(llm, ChatGoogleGenerativeAI)
    assert llm.model == settings.inference_model
    assert llm.temperature == 0.0


def test_get_chat_llm_custom_model_override() -> None:
    """Verify that get_chat_llm honors explicit model and temperature overrides."""
    llm = get_chat_llm(model="custom-override-model", temperature=0.7)
    assert isinstance(llm, ChatGoogleGenerativeAI)
    assert llm.model == "custom-override-model"
    assert llm.temperature == 0.7


def test_get_chat_llm_local_engine(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify that get_chat_llm returns ChatOllama when inference_engine is LOCAL."""
    monkeypatch.setattr(settings, "inference_engine", EngineType.LOCAL)
    monkeypatch.setattr(settings, "inference_model", "llama3.2:3b")
    monkeypatch.setattr(settings, "ollama_or_any_local_endpoint", "http://localhost:11434")

    llm = get_chat_llm()
    assert isinstance(llm, ChatOllama)
    assert llm.model == "llama3.2:3b"
    assert llm.base_url == "http://localhost:11434"
