"""
HC-XCDSS AI Assistant Package
"""

from .context_builder import build_patient_ai_context
from .prompt_builder import (
    build_system_instruction,
    format_analysis_context_for_prompt,
    build_user_prompt,
)
from .safety_validator import validate_user_question, SafetyValidationResult
from .assistant_service import AIAssistantService, PatientAssistantService
from .schemas import (
    ChatMessage,
    AssistantMessageRequest,
    AssistantMessageResponse,
)
from .providers.base import BaseLLMProvider
from .providers.gemini_provider import GeminiLLMProvider

__all__ = [
    "build_patient_ai_context",
    "build_system_instruction",
    "format_analysis_context_for_prompt",
    "build_user_prompt",
    "validate_user_question",
    "SafetyValidationResult",
    "AIAssistantService",
    "PatientAssistantService",
    "ChatMessage",
    "AssistantMessageRequest",
    "AssistantMessageResponse",
    "BaseLLMProvider",
    "GeminiLLMProvider",
]
