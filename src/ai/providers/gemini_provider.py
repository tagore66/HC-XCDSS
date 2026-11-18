"""
HC-XCDSS Gemini LLM Provider

Implements Google Gemini generation via official standard REST API endpoints
with secure environment configuration and graceful fallback.
"""

import os
import json
import urllib.request
import urllib.error
from typing import List, Dict, Any, Optional
from .base import BaseLLMProvider


class GeminiLLMProvider(BaseLLMProvider):
    """
    Production-ready Gemini LLM provider for HC-XCDSS.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
    ):
        self._api_key = api_key or os.getenv("GEMINI_API_KEY", "")
        self._model = model or os.getenv("GEMINI_MODEL") or os.getenv("LLM_MODEL", "gemini-3.7-flash")

    @property
    def provider_name(self) -> str:
        return "gemini"

    @property
    def model_name(self) -> str:
        return self._model

    @property
    def is_configured(self) -> bool:
        return bool(self._api_key and self._api_key.strip())

    def generate_response(
        self,
        system_instruction: str,
        prompt: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        temperature: float = 0.2,
    ) -> Dict[str, Any]:
        """
        Calls Gemini generateContent endpoint with candidate fallback.
        """
        if not self.is_configured:
            raise ValueError(
                "Gemini API key is not configured. Please set GEMINI_API_KEY in your environment."
            )

        candidate_models = [self._model]
        for fallback in ["gemini-3.1-flash-lite", "gemini-3.7-flash"]:
            if fallback not in candidate_models:
                candidate_models.append(fallback)

        last_error = None
        for model_name in candidate_models:
            endpoint = (
                f"https://generativelanguage.googleapis.com/v1beta/models/"
                f"{model_name}:generateContent?key={self._api_key.strip()}"
            )

            # Build contents array from history + current prompt
            contents = []

            if conversation_history:
                for turn in conversation_history:
                    role = "user" if turn.get("role") in ["user", "patient", "professional"] else "model"
                    contents.append({
                        "role": role,
                        "parts": [{"text": turn.get("content", "")}]
                    })

            # Add current user prompt
            contents.append({
                "role": "user",
                "parts": [{"text": prompt}]
            })

            payload = {
                "system_instruction": {
                    "parts": [{"text": system_instruction}]
                },
                "contents": contents,
                "generationConfig": {
                    "temperature": temperature,
                    "maxOutputTokens": 1000,
                }
            }

            req = urllib.request.Request(
                endpoint,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )

            try:
                with urllib.request.urlopen(req, timeout=5) as response:
                    res_body = response.read().decode("utf-8")
                    data = json.loads(res_body)

                    candidates = data.get("candidates", [])
                    if not candidates:
                        continue

                    parts = candidates[0].get("content", {}).get("parts", [])
                    answer_text = "".join(p.get("text", "") for p in parts).strip()

                    if answer_text:
                        return {
                            "text": answer_text,
                            "provider": self.provider_name,
                            "model": model_name,
                        }
            except Exception as e:
                last_error = e
                continue

        raise RuntimeError(f"Gemini generation failed across candidate models: {str(last_error)}")
