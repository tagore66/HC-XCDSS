"""
HC-XCDSS Abstract LLM Provider Interface
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional


class BaseLLMProvider(ABC):
    """
    Abstract base class for LLM providers (Gemini, OpenAI, Anthropic, Mock).
    """

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Name of the provider (e.g. 'gemini', 'mock')."""
        pass

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Name of the model in use (e.g. 'gemini-1.5-flash', 'gemini-2.0-flash')."""
        pass

    @abstractmethod
    def generate_response(
        self,
        system_instruction: str,
        prompt: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        temperature: float = 0.2,
    ) -> Dict[str, Any]:
        """
        Generate text response from the provider given instructions, prompt, and conversation history.

        Returns:
            Dict containing 'text', 'provider', 'model', 'raw_response_metadata' (optional).
        """
        pass
