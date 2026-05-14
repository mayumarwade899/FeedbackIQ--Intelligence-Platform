"""Feedback ingestion and retrieval endpoints."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from core.schemas import FeedbackResponse, FeedbackSubmit, ProcessedFeedbackResponse, PaginatedResponse
from db.database import get_db
from db.models import ProcessedFeedback, RawFeedback

router = APIRouter()


@router.post("/submit", response_model=FeedbackResponse)
async def submit_feedback(
    payload: FeedbackSubmit,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Submit feedback manually — triggers agent pipeline in background."""
    from agents.ingestion_agent import ingest_manual

    feedback = await ingest_manual(
        text=payload.text,
        title=payload.title,
        author=payload.author,
        metadata=payload.metadata,
    )

    async def _process():
        from agents.orchestrator import get_orchestrator
        try:
            await get_orchestrator().process(feedback)
        except Exception as exc:
            import logging
            logging.getLogger(__name__).error("Background processing failed: %s", exc)

    background_tasks.add_task(_process)

    return FeedbackResponse(
        id=feedback.id,
        external_id=feedback.external_id,
        source=feedback.source,
        title=feedback.title,
        body=feedback.body,
        author=feedback.author,
        ingested_at=feedback.ingested_at,
        processed=feedback.processed,
        processing_status=feedback.processing_status,
    )

@router.get("/raw", response_model=List[FeedbackResponse])
async def list_raw_feedback(
    source: Optional[str] = None,
    processed: Optional[bool] = None,
    limit: int = Query(50, le=200),
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
):
    """List raw ingested feedback."""
    q = select(RawFeedback).order_by(RawFeedback.ingested_at.desc())
    if source:
        q = q.where(RawFeedback.source == source)
    if processed is not None:
        q = q.where(RawFeedback.processed == processed)
    q = q.limit(limit).offset(offset)
    result = await db.execute(q)
    rows = result.scalars().all()
    return [
        FeedbackResponse(
            id=r.id, external_id=r.external_id, source=r.source,
            title=r.title, body=r.body, author=r.author,
            ingested_at=r.ingested_at, processed=r.processed,
            processing_status=r.processing_status,
        )
        for r in rows
    ]


@router.get("/processed", response_model=PaginatedResponse[ProcessedFeedbackResponse])
async def list_processed_feedback(
    category: Optional[str] = None,
    priority: Optional[str] = None,
    sentiment: Optional[str] = None,
    review_status: Optional[str] = None,
    limit: int = Query(50, le=200),
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
):
    """List processed feedback with full enrichment data."""
    from core.schemas import PaginatedResponse
    
    q = (
        select(ProcessedFeedback)
        .options(selectinload(ProcessedFeedback.raw))
        .order_by(ProcessedFeedback.processed_at.desc())
    )
    
    count_q = select(func.count()).select_from(ProcessedFeedback)

    if category:
        q = q.where(ProcessedFeedback.category == category)
        count_q = count_q.where(ProcessedFeedback.category == category)
    if priority:
        q = q.where(ProcessedFeedback.priority == priority)
        count_q = count_q.where(ProcessedFeedback.priority == priority)
    if sentiment:
        q = q.where(ProcessedFeedback.sentiment == sentiment)
        count_q = count_q.where(ProcessedFeedback.sentiment == sentiment)
    if review_status:
        q = q.where(ProcessedFeedback.review_status == review_status)
        count_q = count_q.where(ProcessedFeedback.review_status == review_status)

    total = await db.scalar(count_q)

    q = q.limit(limit).offset(offset)
    result = await db.execute(q)
    rows = result.scalars().all()

    return {"items": [_serialize_processed(r) for r in rows], "total": total}


@router.get("/processed/{feedback_id}", response_model=ProcessedFeedbackResponse)
async def get_processed_feedback(feedback_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(ProcessedFeedback)
        .options(selectinload(ProcessedFeedback.raw))
        .where(ProcessedFeedback.id == feedback_id)
    )
    row = result.scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Feedback not found")
    return _serialize_processed(row)


@router.post("/processed/{feedback_id}/review")
async def review_feedback(
    feedback_id: str,
    action: str,
    reviewer: str,
    notes: Optional[str] = None,
    category: Optional[str] = None,
    priority: Optional[str] = None,
    sentiment: Optional[str] = None,
    confidence: Optional[float] = None,
    db: AsyncSession = Depends(get_db),
):
    """Human-in-the-loop review decision."""
    result = await db.execute(
        select(ProcessedFeedback).where(ProcessedFeedback.id == feedback_id)
    )
    feedback = result.scalar_one_or_none()
    if not feedback:
        raise HTTPException(status_code=404, detail="Feedback not found")

    if action not in ("approve", "reject", "modify"):
        raise HTTPException(status_code=400, detail="Invalid action")

    feedback.review_status = action + "d" if action != "modify" else "modified"
    feedback.reviewed_by = reviewer
    feedback.reviewed_at = datetime.utcnow()
    feedback.reviewer_notes = notes

    VALID_CATEGORIES = {"Bug", "Feature Request", "Complaint", "Praise", "Spam", "Question"}
    VALID_PRIORITIES = {"Critical", "High", "Medium", "Low"}
    VALID_SENTIMENTS = {"positive", "negative", "neutral", "mixed"}

    if category and category in VALID_CATEGORIES:
        feedback.category = category
    if priority and priority in VALID_PRIORITIES:
        feedback.priority = priority
    if sentiment and sentiment in VALID_SENTIMENTS:
        feedback.sentiment = sentiment
    if confidence is not None:
        feedback.confidence = max(0.0, min(1.0, confidence))

    await db.commit()
    return {"status": "ok", "review_status": feedback.review_status}


def _serialize_processed(r: ProcessedFeedback) -> ProcessedFeedbackResponse:
    raw_data = None
    if r.raw:
        raw_data = FeedbackResponse(
            id=r.raw.id, external_id=r.raw.external_id, source=r.raw.source,
            title=r.raw.title, body=r.raw.body, author=r.raw.author,
            ingested_at=r.raw.ingested_at, processed=r.raw.processed,
            processing_status=r.raw.processing_status,
        )
    return ProcessedFeedbackResponse(
        id=r.id, raw_id=r.raw_id, category=r.category,
        confidence=r.confidence, priority=r.priority,
        sentiment=r.sentiment, sentiment_score=r.sentiment_score,
        emotion_tags=r.emotion_tags, is_duplicate=r.is_duplicate,
        duplicate_of_id=r.duplicate_of_id,
        impact_summary=r.impact_summary,
        suggested_resolution=r.suggested_resolution,
        key_phrases=r.key_phrases, review_status=r.review_status,
        reviewed_by=r.reviewed_by, reviewed_at=r.reviewed_at,
        reviewer_notes=r.reviewer_notes, processed_at=r.processed_at,
        language=r.language, translated_body=r.translated_body,
        toxicity_score=r.toxicity_score, is_abusive=r.is_abusive,
        emotion_intensity=r.emotion_intensity,
        raw=raw_data,
    )
