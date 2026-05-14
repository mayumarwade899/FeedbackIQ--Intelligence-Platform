"""
Classification Agent — Categorizes feedback using LLM with heuristic fallback.
"""
from __future__ import annotations

import re
from typing import Dict

from agents.base import BaseAgent
from agents.llm_client import get_llm
from core.schemas import AgentState

CATEGORIES = {"Bug", "Feature Request", "Complaint", "Praise", "Spam", "Question"}
PRIORITIES = {"Critical", "High", "Medium", "Low"}

HEURISTIC_RULES = {
    "Bug": ["crash", "error", "broken", "doesn't work", "fails", "bug", "exception", "timeout", "not working"],
    "Feature Request": ["would love", "please add", "feature", "dark mode", "wish", "could you", "request", "suggestion"],
    "Praise": ["amazing", "love", "great", "awesome", "excellent", "perfect", "fantastic", "best"],
    "Complaint": ["expensive", "slow", "poor", "disappointed", "terrible", "worst", "useless"],
    "Spam": ["buy followers", "visit http", "click here", "free money", "lottery", "!!!"],
}

PRIORITY_KEYWORDS = {
    "Critical": ["data loss", "crash", "security", "breach", "urgent", "cannot login", "lost all"],
    "High": ["error", "fails", "broken", "oauth", "login", "export"],
    "Low": ["minor", "nice to have", "suggestion", "cosmetic"],
}

SYSTEM_PROMPT = """You are a product feedback classification expert.
Analyze the feedback and return ONLY a JSON object with these exact keys:
{
  "category": "<Bug|Feature Request|Complaint|Praise|Spam|Question>",
  "priority": "<Critical|High|Medium|Low>",
  "confidence": <0.0-1.0>,
  "rationale": "<1-2 sentence explanation>",
  "language": "<detected ISO 639-1 code>",
  "is_english": <true|false>,
  "translated_text": "<English translation IF not English, else null>"
}

Classification guidelines:
- Bug: Software defects, crashes, errors, unexpected behavior
- Feature Request: New functionality, enhancements, improvements
- Complaint: General dissatisfaction without specific bug
- Praise: Positive feedback, appreciation
- Spam: Unrelated content, advertisements
- Question: User questions or help requests"""


class ClassificationAgent(BaseAgent):
    name = "classification_agent"

    async def _run(self, state: AgentState) -> AgentState:
        text = state.get("text", "")
        title = state.get("title", "")
        effective_text = state.get("translated_text") or text
        full_text = f"Title: {title}\n\n{effective_text}" if title else effective_text

        llm = get_llm()

        usage = None
        if llm.available:
            prompt = f"Classify this feedback:\n\n{full_text[:2000]}"
            result_obj = await llm.generate_json(SYSTEM_PROMPT, prompt)
            result = result_obj["data"]
            usage = result_obj["usage"]
        else:
            result = _heuristic_classify(full_text)

        category = result.get("category", "")
        if category not in CATEGORIES:
            category = _heuristic_classify(full_text)["category"]

        priority = result.get("priority", "")
        if priority not in PRIORITIES:
            priority = _heuristic_priority(full_text.lower(), category)

        raw_confidence = result.get("confidence", 0.0)
        try:
            confidence = float(raw_confidence)
        except (TypeError, ValueError):
            confidence = 0.5
        confidence = max(0.0, min(1.0, confidence))

        state["_last_usage"] = usage
        state["category"] = category
        state["priority"] = priority
        state["confidence"] = confidence
        state["classification_rationale"] = result.get("rationale", "")

        return state

    def _fallback(self, state: AgentState) -> AgentState:
        text = state.get("text", "")
        title = state.get("title", "")
        effective_text = state.get("translated_text") or text
        full_text = f"Title: {title}\n\n{effective_text}" if title else effective_text

        result = _heuristic_classify(full_text)
        
        state["category"] = result.get("category", "Complaint")
        state["priority"] = result.get("priority", "Medium")
        state["confidence"] = result.get("confidence", 0.45)
        state["classification_rationale"] = result.get("rationale", "")
        
        return state


def _heuristic_classify(text: str) -> Dict:
    text_lower = text.lower()
    scores: Dict[str, int] = {cat: 0 for cat in CATEGORIES}

    for cat, keywords in HEURISTIC_RULES.items():
        for kw in keywords:
            if kw in text_lower:
                scores[cat] += 1

    best = max(scores, key=lambda k: scores[k])
    category = best if scores[best] > 0 else "Complaint"
    priority = _heuristic_priority(text_lower, category)

    return {
        "category": category,
        "priority": priority,
        "confidence": 0.45,
        "rationale": "Heuristic keyword-based classification.",
    }


def _heuristic_priority(text: str, category: str) -> str:
    text_lower = text.lower()
    for priority, keywords in PRIORITY_KEYWORDS.items():
        if any(kw in text_lower for kw in keywords):
            return priority

    defaults = {
        "Bug": "High", "Feature Request": "Medium",
        "Complaint": "Medium", "Praise": "Low",
        "Spam": "Low", "Question": "Low",
    }
    return defaults.get(category, "Medium")
