"""
LLM Client — Gemini wrapper with structured output parsing and fallbacks.
"""
from __future__ import annotations

import json
import logging
import os
from typing import Any, Dict, Optional

import json5

logger = logging.getLogger(__name__)


class LLMClient:
    """Async Gemini LLM client with JSON output parsing."""

    def __init__(self):
        from core.config import settings
        self.api_key = settings.GOOGLE_API_KEY
        self.model = settings.GEMINI_MODEL
        self.temperature = settings.GEMINI_TEMPERATURE
        self.max_tokens = settings.GEMINI_MAX_TOKENS
        self._client = None

        if self.api_key:
            try:
                from google import genai
                self._client = genai.Client(api_key=self.api_key)
                logger.info("Gemini LLM initialized: model=%s", self.model)
            except Exception as exc:
                logger.warning("Gemini init failed: %s — heuristic mode", exc)

    @property
    def available(self) -> bool:
        return self._client is not None

    async def generate(self, system_prompt: str, user_prompt: str) -> Dict[str, Any]:
        """Generate text using Gemini API and return content + usage."""
        if not self._client:
            raise RuntimeError("LLM not available")

        from google.genai import types

        full_prompt = f"{system_prompt}\n\n{user_prompt}"

        response = await self._client.aio.models.generate_content(
            model=self.model,
            contents=full_prompt,
            config=types.GenerateContentConfig(
                temperature=self.temperature,
                max_output_tokens=self.max_tokens,
            ),
        )
        
        usage = response.usage_metadata
        return {
            "text": response.text,
            "usage": {
                "prompt_tokens": usage.prompt_token_count,
                "candidates_tokens": usage.candidates_token_count,
                "total_tokens": usage.total_token_count,
            }
        }

    async def generate_json(
        self, system_prompt: str, user_prompt: str
    ) -> Dict[str, Any]:
        """Generate and parse a JSON response from the LLM, including usage."""
        result = await self.generate(system_prompt, user_prompt)
        parsed = _parse_json(result["text"])
        return {
            "data": parsed,
            "usage": result["usage"]
        }


def _parse_json(text: str) -> Dict[str, Any]:
    """Parse JSON from LLM output, stripping markdown fences."""
    text = text.strip()
    if text.startswith("```"):
        text = text.lstrip("`").strip()
        if text.lower().startswith("json"):
            text = text[4:].strip()
        text = text.rstrip("`").strip()
    try:
        return json5.loads(text)
    except Exception:
        try:
            return json.loads(text)
        except Exception as exc:
            raise ValueError(f"Could not parse LLM JSON: {exc}\nRaw: {text[:300]}")


# Singleton instance
_llm_client: Optional[LLMClient] = None


def get_llm() -> LLMClient:
    global _llm_client
    if _llm_client is None:
        _llm_client = LLMClient()
    return _llm_client
