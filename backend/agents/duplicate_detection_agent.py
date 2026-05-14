"""
Duplicate Detection Agent — Semantic deduplication with text normalisation.

Improvements over v1:
- Text normalised before embedding: lowercase, repeated-word collapse, punctuation strip.
- TF-IDF bag-of-words embeddings (dim=256) for finer-grained resolution.
- Cluster counting: when a duplicate is found the original's duplicate_count is
  incremented in-place so the UI surfaces "N similar reports" rather than N separate items.
- Configurable similarity threshold via settings.SIMILARITY_THRESHOLD.
- No LLM calls — 100 % local, sub-50 ms per item.
"""
from __future__ import annotations

import hashlib
import logging
import math
import re
from collections import Counter
from typing import Dict, List, Optional, Tuple

from agents.base import BaseAgent
from core.config import settings
from core.schemas import AgentState

logger = logging.getLogger(__name__)

_STOP_WORDS = {
    "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "could",
    "should", "may", "might", "shall", "can", "i", "my", "me", "we",
    "you", "your", "it", "its", "this", "that", "they", "them", "their",
    "and", "or", "but", "if", "in", "on", "at", "to", "for", "of", "with",
    "by", "from", "as", "so", "not", "no", "up", "out", "about", "just",
    "also", "app", "please", "fix", "really", "very", "more", "now",
}


def _normalise(text: str) -> str:
    """
    Normalise review text for semantic comparison:
      1. Lowercase
      2. Strip URLs, mentions, hashtags
      3. Remove all non-alphanumeric characters except spaces
      4. Collapse repeated words (e.g. "crash crash crash" → "crash")
      5. Remove stop-words
      6. Collapse whitespace
    """
    text = text.lower()
    text = re.sub(r"https?://\S+", " ", text)
    text = re.sub(r"[@#]\w+", " ", text)
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\b(\w+)(\s+\1){2,}\b", r"\1", text)
    tokens = [t for t in text.split() if t not in _STOP_WORDS and len(t) > 1]
    return " ".join(tokens)


def _tfidf_embedding(text: str, dim: int = 256) -> List[float]:
    """Bag-of-words TF-IDF-style embedding with L2 normalisation (dim=256)."""
    tokens = text.split()
    if not tokens:
        return [0.0] * dim

    counts = Counter(tokens)
    total = sum(counts.values())

    vec = [0.0] * dim
    for word, count in counts.items():
        tf = count / total
        idx = int(hashlib.md5(word.encode()).hexdigest(), 16) % dim
        vec[idx] += tf

    norm = math.sqrt(sum(x * x for x in vec)) or 1.0
    return [x / norm for x in vec]


def _cosine_similarity(a: List[float], b: List[float]) -> float:
    if len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a)) or 1.0
    norm_b = math.sqrt(sum(y * y for y in b)) or 1.0
    return dot / (norm_a * norm_b)


class DuplicateDetectionAgent(BaseAgent):
    name = "duplicate_detection_agent"

    def __init__(self):
        super().__init__()
        self._embedding_cache: Dict[str, List[float]] = {}

    async def _run(self, state: AgentState) -> AgentState:
        raw_text = state.get("translated_text") or state.get("text", "")
        raw_feedback_id = state.get("raw_feedback_id", "")

        normalised = _normalise(raw_text)
        embedding = _tfidf_embedding(normalised)
        state["embedding"] = embedding

        similar_id, score = await self._find_similar(embedding, exclude_id=raw_feedback_id)

        threshold = settings.SIMILARITY_THRESHOLD
        is_dup = bool(similar_id and score >= threshold)

        state["is_duplicate"] = is_dup
        state["duplicate_of_id"] = similar_id if (similar_id and score >= 0.4) else None
        state["similarity_score"] = score if similar_id else None

        if is_dup:
            logger.info(
                "Duplicate detected: feedback=%s similar_to=%s score=%.3f",
                raw_feedback_id, similar_id, score,
            )
            await self._increment_duplicate_count(similar_id)
        elif similar_id and score >= 0.4:
            logger.info(
                "Near-duplicate found: feedback=%s similar_to=%s score=%.3f",
                raw_feedback_id, similar_id, score,
            )

        return state

    async def _find_similar(
        self, embedding: List[float], exclude_id: str
    ) -> Tuple[Optional[str], float]:
        """Query stored embeddings and return (most_similar_id, score)."""
        try:
            from db.database import AsyncSessionLocal
            from db.models import ProcessedFeedback
            from sqlalchemy import select

            async with AsyncSessionLocal() as session:
                result = await session.execute(
                    select(ProcessedFeedback.id, ProcessedFeedback.embedding)
                    .where(ProcessedFeedback.embedding.isnot(None))
                    .limit(500)
                )
                rows = result.fetchall()

            best_id = None
            best_score = 0.0

            for row_id, stored_emb in rows:
                if stored_emb and str(row_id) != exclude_id:
                    if len(stored_emb) != len(embedding):
                        stored_emb = (stored_emb + [0.0] * 256)[:256]
                    score = _cosine_similarity(embedding, stored_emb)
                    if score > best_score:
                        best_score = score
                        best_id = str(row_id)

            return best_id, best_score

        except Exception as exc:
            logger.warning("Duplicate detection DB query failed: %s", exc)
            return None, 0.0

    async def _increment_duplicate_count(self, processed_id: str) -> None:
        """
        Increment the duplicate_count on the representative (original) ProcessedFeedback
        so the UI can surface "N similar reports" without storing every duplicate copy.
        """
        try:
            from db.database import AsyncSessionLocal
            from db.models import ProcessedFeedback
            from sqlalchemy import select

            async with AsyncSessionLocal() as session:
                res = await session.execute(
                    select(ProcessedFeedback).where(ProcessedFeedback.id == processed_id)
                )
                original = res.scalar_one_or_none()
                if original:
                    current = getattr(original, "duplicate_count", None) or 0
                    original.duplicate_count = current + 1
                    session.add(original)
                    await session.commit()
        except Exception as exc:
            logger.warning("Failed to increment duplicate_count for %s: %s", processed_id, exc)
