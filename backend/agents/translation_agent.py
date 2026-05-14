"""
Translation Agent — Detects language and translates non-English feedback to English.
Uses Gemini for detection + translation (no extra API keys required).
Falls back gracefully if translation fails — pipeline continues with original text.
"""
from __future__ import annotations

import logging
import re

from agents.base import BaseAgent
from agents.llm_client import get_llm
from core.schemas import AgentState

logger = logging.getLogger(__name__)

_ENGLISH_CODES = {"en", "english"}

DETECT_PROMPT = """You are a language detection expert.
Identify the language of the following text and return a JSON object.

Return ONLY valid JSON with this exact structure:
{
  "language": "<ISO 639-1 code, e.g. en, ar, id, es, fr, pt, hi, zh, ja, ko>",
  "language_name": "<Full English name, e.g. English, Arabic, Indonesian>",
  "is_english": <true or false>,
  "confidence": <0.0 to 1.0>
}"""

TRANSLATE_PROMPT = """You are a professional translator.
Translate the following text to English accurately.
Preserve the original meaning, tone, and sentiment.
If the text contains slang or informal language, keep that tone in English.

Return ONLY valid JSON with this exact structure:
{
  "translated_text": "<English translation>",
  "translation_notes": "<optional: brief note about any nuances>"
}"""


class TranslationAgent(BaseAgent):
    name = "translation_agent"

    async def _run(self, state: AgentState) -> AgentState:
        text = state.get("text", "").strip()

        if not text:
            state["language"] = "en"
            state["is_english"] = True
            state["translated_text"] = text
            return state

        llm = get_llm()

        if llm.available:
            detect_result = await llm.generate_json(
                DETECT_PROMPT,
                f"Detect the language of this text:\n\n{text[:500]}"
            )
            detection = detect_result.get("data", {})
            usage = detect_result.get("usage")
        else:
            detection = _heuristic_detect(text)
            usage = None

        language_code = detection.get("language", "en").lower()
        language_name = detection.get("language_name", "English")
        is_english = detection.get("is_english", True)

        state["language"] = language_code
        state["is_english"] = is_english
        state["_last_usage"] = usage

        logger.info(
            "Language detected: %s (%s) is_english=%s for feedback=%s",
            language_name, language_code, is_english,
            state.get("raw_feedback_id", "unknown")
        )

        if is_english or language_code in _ENGLISH_CODES:
            state["translated_text"] = text
            return state

        if llm.available:
            translate_result = await llm.generate_json(
                TRANSLATE_PROMPT,
                f"Translate this {language_name} text to English:\n\n{text[:1500]}"
            )
            translation = translate_result.get("data", {})
            translated = translation.get("translated_text", text)
            state["_last_usage"] = translate_result.get("usage")
        else:
            translated = text

        state["translated_text"] = translated

        logger.info(
            "Translated [%s → EN] feedback=%s | Original: %s... | Translated: %s...",
            language_code,
            state.get("raw_feedback_id", "unknown"),
            text[:60],
            translated[:60]
        )

        return state

    def _fallback(self, state: AgentState) -> AgentState:
        text = state.get("text", "").strip()
        detection = _heuristic_detect(text)
        
        state["language"] = detection.get("language", "en").lower()
        state["is_english"] = detection.get("is_english", True)
        state["translated_text"] = text
        
        return state


def _heuristic_detect(text: str) -> dict:
    """Simple heuristic fallback when LLM is unavailable."""
    if re.search(r'[\u0600-\u06FF]', text):
        return {"language": "ar", "language_name": "Arabic", "is_english": False, "confidence": 0.9}
    if re.search(r'[\u4e00-\u9fff\u3040-\u309f\u30a0-\u30ff]', text):
        return {"language": "zh", "language_name": "Chinese/Japanese", "is_english": False, "confidence": 0.9}
    if re.search(r'[\uac00-\ud7af]', text):
        return {"language": "ko", "language_name": "Korean", "is_english": False, "confidence": 0.9}
    return {"language": "en", "language_name": "English", "is_english": True, "confidence": 0.7}
