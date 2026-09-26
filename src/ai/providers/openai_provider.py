"""
HC-XCDSS OpenAI LLM Provider

Implements OpenAI Chat Completion endpoint with secure environment configuration
and standard provider abstraction.
"""

import os
import json
import urllib.request
import urllib.error
from typing import List, Dict, Any, Optional
from .base import BaseLLMProvider


class OpenAILLMProvider(BaseLLMProvider):
    """
    OpenAI-compatible LLM provider for HC-XCDSS.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
    ):
        self._api_key = api_key or os.getenv("OPENAI_API_KEY", "")
        self._model = model or os.getenv("OPENAI_MODEL") or os.getenv("LLM_MODEL", "gpt-4o-mini")

    @property
    def provider_name(self) -> str:
        return "openai"

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
        Calls OpenAI /v1/chat/completions endpoint.
        """
        if not self.is_configured:
            raise ValueError(
                "OpenAI API key is not configured. Please set OPENAI_API_KEY in your environment."
            )

        endpoint = "https://api.openai.com/v1/chat/completions"

        messages = [
            {"role": "system", "content": system_instruction}
        ]

        if conversation_history:
            for turn in conversation_history:
                role = "user" if turn.get("role") in ["user", "patient", "professional"] else "assistant"
                messages.append({
                    "role": role,
                    "content": turn.get("content", "")
                })

        messages.append({
            "role": "user",
            "content": prompt
        })

        payload = {
            "model": self._model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": 1000,
        }

        req = urllib.request.Request(
            endpoint,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self._api_key.strip()}"
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=30) as response:
                res_body = response.read().decode("utf-8")
                data = json.loads(res_body)

                choices = data.get("choices", [])
                if not choices:
                    raise RuntimeError("OpenAI returned no choices in response.")

                answer_text = choices[0].get("message", {}).get("content", "").strip()

                return {
                    "text": answer_text,
                    "provider": self.provider_name,
                    "model": self.model_name,
                }
        except urllib.error.HTTPError as http_err:
            try:
                err_detail = http_err.read().decode("utf-8")
                err_json = json.loads(err_detail)
                msg = err_json.get("error", {}).get("message", str(http_err))
            except Exception:
                msg = str(http_err)
            raise RuntimeError(f"OpenAI API HTTP Error ({http_err.code}): {msg}")
        except Exception as e:
            raise RuntimeError(f"OpenAI generation failed: {str(e)}")
