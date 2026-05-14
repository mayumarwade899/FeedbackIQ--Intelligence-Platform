"""
Orchestrator Agent — LangGraph StateGraph pipeline coordinating all agents.

Updated pipeline order (v2.2):
  translate → classify → [spam gate] → sentiment → [toxicity gate]
      → [parallel: duplicate] → [duplicate gate] → insights → ticket

Key routing nodes:
  - spam gate:     category == "Spam"      → END (no further processing)
  - toxicity gate: skip_processing == True → END (extreme toxic review)
  - duplicate gate: is_duplicate == True   → END (no ticket for duplicates)
"""
from __future__ import annotations

import asyncio
import logging
import time
import uuid
from datetime import datetime
from typing import List

from langgraph.graph import END, StateGraph

from agents.classification_agent import ClassificationAgent
from agents.duplicate_detection_agent import DuplicateDetectionAgent
from agents.insights_agent import InsightsAgent
from agents.sentiment_agent import SentimentAgent
from agents.ticket_generation_agent import TicketGenerationAgent
from agents.translation_agent import TranslationAgent
from core.schemas import AgentState
from db.database import AsyncSessionLocal
from db.models import AgentRun, ProcessedFeedback, RawFeedback, Ticket
from sqlalchemy import select

logger = logging.getLogger(__name__)


def _ticket_number(source: str) -> str:
    ts = datetime.utcnow().strftime("%y%m%d")
    uid = str(uuid.uuid4())[:6].upper()
    prefix = {"github": "GH", "reddit": "RD", "manual": "MN", "api": "AP"}.get(source, "FB")
    return f"{prefix}-{ts}-{uid}"


def _route_after_classification(state: AgentState) -> str:
    """Skip all further processing for spam reviews."""
    if state.get("category") == "Spam":
        return "end_spam"
    return "run_sentiment"


def _route_after_toxicity(state: AgentState) -> str:
    """
    Extreme toxic reviews are silently dropped here.
    Soft-toxic and clean reviews continue to duplicate detection.
    """
    if state.get("skip_processing"):
        return "end_toxic"
    return "run_duplicate"


def _route_after_duplicate(state: AgentState) -> str:
    """Duplicate reviews skip insight/ticket generation — the cluster counter was already bumped."""
    if state.get("is_duplicate"):
        return "end_duplicate"
    return "run_insights"


class FeedbackOrchestrator:
    """
    LangGraph-based orchestrator that runs all agents in sequence with routing.
    """

    def __init__(self):
        self.translator = TranslationAgent()
        self.classifier = ClassificationAgent()
        self.sentiment = SentimentAgent()
        self.duplicate_detector = DuplicateDetectionAgent()
        self.insights = InsightsAgent()
        self.ticket_generator = TicketGenerationAgent()

        self.graph = self._build_graph()
        self.compiled = self.graph.compile()

    def _build_graph(self) -> StateGraph:
        g = StateGraph(AgentState)

        g.add_node("translate",  self._translate)
        g.add_node("classify",   self._classify)
        g.add_node("sentiment",  self._sentiment)
        g.add_node("duplicate",  self._duplicate)
        g.add_node("insights",   self._insights)
        g.add_node("ticket",     self._ticket)

        g.set_entry_point("translate")
        g.add_edge("translate", "classify")

        g.add_conditional_edges(
            "classify",
            _route_after_classification,
            {
                "run_sentiment": "sentiment",
                "end_spam": END,
            },
        )

        g.add_conditional_edges(
            "sentiment",
            _route_after_toxicity,
            {
                "run_duplicate": "duplicate",
                "end_toxic": END,
            },
        )

        g.add_conditional_edges(
            "duplicate",
            _route_after_duplicate,
            {
                "run_insights": "insights",
                "end_duplicate": END,
            },
        )

        g.add_edge("insights", "ticket")
        g.add_edge("ticket", END)

        return g

    async def _translate(self, state: AgentState) -> AgentState:
        logger.info("--- [Pipeline] Translation | id=%s ---", state["raw_feedback_id"])
        res = await self.translator.execute(state)
        logger.info("--- [Pipeline] Translation done | lang=%s is_english=%s ---",
                    res.get("language"), res.get("is_english"))
        return res

    async def _classify(self, state: AgentState) -> AgentState:
        logger.info("--- [Pipeline] Classification | id=%s ---", state["raw_feedback_id"])
        res = await self.classifier.execute(state)
        logger.info("--- [Pipeline] Classification done | category=%s priority=%s ---",
                    res.get("category"), res.get("priority"))
        return res

    async def _sentiment(self, state: AgentState) -> AgentState:
        logger.info("--- [Pipeline] Sentiment + Toxicity ---")
        res = await self.sentiment.execute(state)
        logger.info(
            "--- [Pipeline] Sentiment done | sentiment=%s toxicity=%.2f action=%s ---",
            res.get("sentiment"),
            res.get("toxicity_score", 0.0),
            res.get("moderation_action", "none"),
        )
        return res

    async def _duplicate(self, state: AgentState) -> AgentState:
        logger.info("--- [Pipeline] Duplicate Detection ---")
        res = await self.duplicate_detector.execute(state)
        logger.info("--- [Pipeline] Duplicate done | is_duplicate=%s score=%s ---",
                    res.get("is_duplicate"), res.get("similarity_score"))
        return res

    async def _insights(self, state: AgentState) -> AgentState:
        logger.info("--- [Pipeline] Insights extraction ---")
        res = await self.insights.execute(state)
        logger.info("--- [Pipeline] Insights done ---")
        return res

    async def _ticket(self, state: AgentState) -> AgentState:
        logger.info("--- [Pipeline] Ticket generation ---")
        res = await self.ticket_generator.execute(state)
        logger.info("--- [Pipeline] Ticket done | title=%s ---", res.get("ticket_title", "")[:60])
        return res

    async def process_by_id(self, fb_id: str) -> AgentState:
        """
        Fetch record by ID in a fresh session and process it.
        Avoids session conflicts in parallel batches.
        """
        async with AsyncSessionLocal() as session:
            res = await session.execute(select(RawFeedback).where(RawFeedback.id == fb_id))
            raw = res.scalar_one_or_none()
            if not raw:
                raise ValueError(f"Feedback {fb_id} not found")

            fb_id_str  = str(raw.id)
            fb_source  = raw.source
            fb_body    = raw.body
            fb_title   = raw.title
            fb_meta    = raw.raw_metadata or {}

        initial_state: AgentState = {
            "raw_feedback_id": fb_id_str,
            "source": fb_source,
            "text": fb_body,
            "title": fb_title,
            "metadata": fb_meta,
            "errors": [],
            "agent_traces": [],
            "processing_start": time.monotonic(),
        }

        try:
            final_state = await self.compiled.ainvoke(initial_state)
        except Exception as exc:
            logger.error("Pipeline failed for %s: %s", fb_id_str, exc)
            async with AsyncSessionLocal() as session:
                res = await session.execute(select(RawFeedback).where(RawFeedback.id == fb_id))
                raw_fresh = res.scalar_one_or_none()
                if raw_fresh:
                    await self._mark_failed(raw_fresh, str(exc), session)
                await session.commit()
            raise

        async with AsyncSessionLocal() as session:
            res = await session.execute(select(RawFeedback).where(RawFeedback.id == fb_id))
            raw_fresh = res.scalar_one_or_none()
            if raw_fresh:
                await self._persist_results(raw_fresh, final_state, session)
            await session.commit()

        return final_state

    async def process(self, raw_feedback: RawFeedback) -> AgentState:
        """Run the full pipeline for a single RawFeedback ORM object."""
        initial_state: AgentState = {
            "raw_feedback_id": raw_feedback.id,
            "source": raw_feedback.source,
            "text": raw_feedback.body,
            "title": raw_feedback.title,
            "metadata": raw_feedback.raw_metadata or {},
            "errors": [],
            "agent_traces": [],
            "processing_start": time.monotonic(),
        }

        try:
            final_state = await self.compiled.ainvoke(initial_state)
            await self._persist_results(raw_feedback, final_state)
            return final_state
        except Exception as exc:
            logger.error("Pipeline failed for %s: %s", raw_feedback.id, exc)
            await self._mark_failed(raw_feedback, str(exc))
            raise

    async def _persist_results(self, raw: RawFeedback, state: AgentState, session=None):
        """Persist processed feedback, ticket, and agent run traces to DB."""
        from db.database import AsyncSessionLocal

        async def _do_persist(s):
            processed = ProcessedFeedback(
                id=str(uuid.uuid4()),
                raw_id=raw.id,
                category=state.get("category", "Complaint"),
                confidence=state.get("confidence", 0.5),
                priority=state.get("priority", "Medium"),
                sentiment=state.get("sentiment", "neutral"),
                sentiment_score=state.get("sentiment_score", 0.0),
                emotion_tags=state.get("emotion_tags", []),
                emotion_intensity=state.get("emotion_intensity", 0.0),
                toxicity_score=state.get("toxicity_score", 0.0),
                is_abusive=state.get("is_abusive", False),
                language=state.get("language"),
                translated_body=state.get("translated_text"),
                is_duplicate=state.get("is_duplicate", False),
                duplicate_of_id=state.get("duplicate_of_id"),
                similarity_score=state.get("similarity_score"),
                embedding=state.get("embedding"),
                impact_summary=state.get("impact_summary"),
                suggested_resolution=state.get("suggested_resolution"),
                key_phrases=state.get("key_phrases", []),
                technical_details=state.get("technical_details", {}),
                review_status="pending",
                agent_version="2.2.0",
            )
            s.add(processed)
            await s.flush()

            skip = state.get("skip_processing", False)
            is_dup = state.get("is_duplicate", False)
            if not is_dup and not skip and state.get("ticket_title"):
                ticket = Ticket(
                    id=str(uuid.uuid4()),
                    ticket_number=_ticket_number(raw.source),
                    feedback_id=processed.id,
                    title=state["ticket_title"],
                    description=state.get("ticket_description", ""),
                    category=state.get("category", "Complaint"),
                    priority=state.get("priority", "Medium"),
                    impact_summary=state.get("impact_summary"),
                    suggested_resolution=state.get("suggested_resolution"),
                    labels=state.get("ticket_labels", []),
                    status="open",
                )
                s.add(ticket)

            for trace in state.get("agent_traces", []):
                run = AgentRun(
                    id=str(uuid.uuid4()),
                    raw_feedback_id=raw.id,
                    agent_name=trace.get("agent", "unknown"),
                    status=trace.get("status", "unknown"),
                    latency_ms=trace.get("latency_ms"),
                    tokens_used=trace.get("total_tokens", 0),
                    output_data={
                        "prompt_tokens": trace.get("prompt_tokens", 0),
                        "completion_tokens": trace.get("completion_tokens", 0),
                    },
                    error_message=trace.get("error"),
                    started_at=datetime.utcnow(),
                    completed_at=datetime.utcnow(),
                )
                s.add(run)

            raw.processed = True
            raw.processing_status = "done"
            s.add(raw)

        if session is not None:
            await _do_persist(session)
        else:
            async with AsyncSessionLocal() as s:
                await _do_persist(s)
                await s.commit()

    async def _mark_failed(self, raw: RawFeedback, error: str, session=None):
        from db.database import AsyncSessionLocal

        async def _do_mark(s):
            raw.processed = False
            raw.processing_status = "failed"
            s.add(raw)
            s.add(AgentRun(
                id=str(uuid.uuid4()),
                raw_feedback_id=raw.id,
                agent_name="orchestrator",
                status="failed",
                error_message=error[:500],
                started_at=datetime.utcnow(),
                completed_at=datetime.utcnow(),
            ))

        if session is not None:
            await _do_mark(session)
        else:
            async with AsyncSessionLocal() as s:
                await _do_mark(s)
                await s.commit()

_orchestrator: FeedbackOrchestrator | None = None


def get_orchestrator() -> FeedbackOrchestrator:
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = FeedbackOrchestrator()
    return _orchestrator
