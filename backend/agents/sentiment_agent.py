"""
Sentiment Analysis Agent — Sentiment, emotion, and two-tier toxicity moderation.

Moderation tiers (configured in settings):
  SOFT   (toxicity_score >= TOXICITY_SOFT_THRESHOLD):
    - Mask abusive/profane words in the text.
    - Continue processing — insights and ticket are still generated.
    - state["moderation_action"] = "masked"

  EXTREME (toxicity_score >= TOXICITY_EXTREME_THRESHOLD):
    - Set state["skip_processing"] = True so the orchestrator exits early.
    - No insights or ticket are generated for this review.
    - state["moderation_action"] = "skipped"

Note: Toxicity check always runs on the TRANSLATED (English) text, never on
the raw non-English original, ensuring non-English abusive content is caught.
"""
from __future__ import annotations

import re

from agents.base import BaseAgent
from agents.llm_client import get_llm
from core.config import settings
from core.schemas import AgentState

SYSTEM_PROMPT = """You are an expert sentiment analyser and content moderator.
Analyse the text and return ONLY this JSON:
{
  "sentiment": "<positive|negative|neutral|mixed>",
  "sentiment_score": <-1.0 to 1.0>,
  "emotion_tags": ["<frustration|joy|disappointment|excitement|anger|satisfaction|confusion|urgency>"],
  "emotion_intensity": <0.0 to 1.0>,
  "toxicity_score": <0.0 to 1.0>,
  "is_abusive": <true|false>,
  "masked_text": "<text with abusive words replaced by ***, only if is_abusive is true, else null>"
}

Rules:
- sentiment_score: -1.0 = very negative, 1.0 = very positive
- toxicity_score: 1.0 = highly toxic / abusive
- masked_text: Only provide when is_abusive is true. Preserve the non-abusive parts of the review intact."""

POSITIVE_WORDS = ["love", "great", "amazing", "excellent", "perfect", "fantastic", "helpful", "awesome", "best"]
NEGATIVE_WORDS = ["crash", "broken", "terrible", "awful", "hate", "worst", "useless", "poor", "fail", "error", "bug"]

_PROFANITY_RE = re.compile(
    r"\b(fuck|shit|ass|bitch|bastard|damn|crap|piss|dick|cunt|asshole)\b",
    re.IGNORECASE,
)


class SentimentAgent(BaseAgent):
    name = "sentiment_agent"

    async def _run(self, state: AgentState) -> AgentState:
        text = state.get("translated_text") or state.get("text", "")
        llm = get_llm()

        usage = None
        if llm.available:
            result_obj = await llm.generate_json(
                SYSTEM_PROMPT,
                f"Analyse sentiment and toxicity of this feedback:\n\n{text[:1500]}"
            )
            result = result_obj["data"]
            usage = result_obj["usage"]
        else:
            result = _heuristic_sentiment(text)

        state["_last_usage"] = usage
        state["sentiment"] = result.get("sentiment", "neutral")
        state["sentiment_score"] = float(result.get("sentiment_score", 0.0))
        state["emotion_tags"] = result.get("emotion_tags", [])
        state["emotion_intensity"] = float(result.get("emotion_intensity", 0.5))
        state["toxicity_score"] = float(result.get("toxicity_score", 0.0))
        state["is_abusive"] = bool(result.get("is_abusive", False))
        state["masked_text"] = result.get("masked_text")

        toxicity = state["toxicity_score"]
        extreme_threshold = settings.TOXICITY_EXTREME_THRESHOLD
        soft_threshold = settings.TOXICITY_SOFT_THRESHOLD

        if toxicity >= extreme_threshold:
            state["skip_processing"] = True
            state["moderation_action"] = "skipped"
        elif toxicity >= soft_threshold or state["is_abusive"]:
            state["skip_processing"] = False
            state["moderation_action"] = "masked"
            if not state.get("masked_text"):
                state["masked_text"] = _mask_profanity(text)
        else:
            state["skip_processing"] = False
            state["moderation_action"] = "none"

        return state

    def _fallback(self, state: AgentState) -> AgentState:
        text = state.get("translated_text") or state.get("text", "")
        result = _heuristic_sentiment(text)

        state["sentiment"] = result.get("sentiment", "neutral")
        state["sentiment_score"] = float(result.get("sentiment_score", 0.0))
        state["emotion_tags"] = result.get("emotion_tags", [])
        state["emotion_intensity"] = 0.5
        state["toxicity_score"] = 0.0
        state["is_abusive"] = False
        state["masked_text"] = None
        state["skip_processing"] = False
        state["moderation_action"] = "none"

        return state

def _heuristic_sentiment(text: str) -> dict:
    text_lower = text.lower()
    pos = sum(1 for w in POSITIVE_WORDS if w in text_lower)
    neg = sum(1 for w in NEGATIVE_WORDS if w in text_lower)

    has_profanity = bool(_PROFANITY_RE.search(text))
    tox_score = 0.6 if has_profanity else 0.0

    if pos > neg:
        sentiment, score, emotions = "positive", min(0.8, pos * 0.2), ["satisfaction"]
    elif neg > pos:
        sentiment, score, emotions = "negative", max(-0.8, neg * -0.2), ["frustration"]
    else:
        sentiment, score, emotions = "neutral", 0.0, []

    return {
        "sentiment": sentiment,
        "sentiment_score": score,
        "emotion_tags": emotions,
        "emotion_intensity": 0.5,
        "toxicity_score": tox_score,
        "is_abusive": has_profanity,
        "masked_text": _mask_profanity(text) if has_profanity else None,
    }


def _mask_profanity(text: str) -> str:
    """Replace matched profanity with asterisks of the same length."""
    def _replace(m: re.Match) -> str:
        return "*" * len(m.group())
    return _PROFANITY_RE.sub(_replace, text)
