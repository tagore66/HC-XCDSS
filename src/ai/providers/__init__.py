import os
from typing import Optional
from pathlib import Path
from dotenv import load_dotenv
from .base import BaseLLMProvider
from .gemini_provider import GeminiLLMProvider
from .openai_provider import OpenAILLMProvider
from .mock_provider import MockLLMProvider


def get_llm_provider(
    provider_type: Optional[str] = None,
    api_key: Optional[str] = None,
    model: Optional[str] = None,
) -> BaseLLMProvider:
    """
    Factory creating configured LLM provider based on environment variables or explicit parameters.
    Default: GeminiLLMProvider if GEMINI_API_KEY is present, OpenAILLMProvider if OPENAI_API_KEY is present, else MockLLMProvider.
    """
    # Ensure root .env is loaded into process environment if present
    project_root = Path(__file__).resolve().parents[3]
    env_path = project_root / ".env"
    if env_path.exists():
        load_dotenv(dotenv_path=env_path)
    else:
        load_dotenv()

    prov_name = (provider_type or os.getenv("LLM_PROVIDER", "gemini")).lower().strip()

    if prov_name == "mock":
        return MockLLMProvider(model_name=model or os.getenv("LLM_MODEL", "mock-decision-support-v1"))

    if prov_name == "openai":
        openai_prov = OpenAILLMProvider(api_key=api_key, model=model)
        if openai_prov.is_configured:
            return openai_prov
        return MockLLMProvider(model_name=model or os.getenv("LLM_MODEL", "mock-decision-support-v1"))

    # Gemini provider
    gemini = GeminiLLMProvider(api_key=api_key, model=model)
    if gemini.is_configured:
        return gemini

    # Fallback to Mock Provider if no API key is present
    return MockLLMProvider(model_name=model or os.getenv("LLM_MODEL", "mock-decision-support-v1"))


__all__ = [
    "BaseLLMProvider",
    "GeminiLLMProvider",
    "OpenAILLMProvider",
    "MockLLMProvider",
    "get_llm_provider",
]
