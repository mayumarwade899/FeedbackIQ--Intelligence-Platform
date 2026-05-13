"""Analytics and intelligence layer endpoints."""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import List

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.schemas import AnalyticsOverview, TrendPoint
from core.config import settings
from db.database import get_db
from db.models import AgentRun, ProcessedFeedback, RawFeedback, Ticket

router = APIRouter()


@router.get("/overview", response_model=AnalyticsOverview)
async def get_overview(db: AsyncSession = Depends(get_db)):
    now = datetime.utcnow()
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)

    # Total feedback (only completed ones)
    total = (await db.execute(select(func.count(RawFeedback.id)).where(RawFeedback.processed == True))).scalar() or 0

    # Processed today
    processed_today = (
        await db.execute(
            select(func.count(ProcessedFeedback.id)).where(
                ProcessedFeedback.processed_at >= today
            )
        )
    ).scalar() or 0

    # Pending review
    pending_review = (
        await db.execute(
            select(func.count(ProcessedFeedback.id)).where(
                ProcessedFeedback.review_status == "pending"
            )
        )
    ).scalar() or 0

    # Open tickets
    open_tickets = (
        await db.execute(
            select(func.count(Ticket.id)).where(Ticket.status == "open")
        )
    ).scalar() or 0

    # Avg confidence
    avg_conf = (
        await db.execute(select(func.avg(ProcessedFeedback.confidence)))
    ).scalar() or 0.0

    # Category distribution
    cat_rows = await db.execute(
        select(ProcessedFeedback.category, func.count(ProcessedFeedback.id)).group_by(
            ProcessedFeedback.category
        )
    )
    category_dist = {r[0]: r[1] for r in cat_rows.fetchall()}

    # Priority distribution
    pri_rows = await db.execute(
        select(ProcessedFeedback.priority, func.count(ProcessedFeedback.id)).group_by(
            ProcessedFeedback.priority
        )
    )
    priority_dist = {r[0]: r[1] for r in pri_rows.fetchall()}

    # Sentiment distribution
    sent_rows = await db.execute(
        select(ProcessedFeedback.sentiment, func.count(ProcessedFeedback.id)).group_by(
            ProcessedFeedback.sentiment
        )
    )
    sentiment_dist = {r[0]: r[1] for r in sent_rows.fetchall()}

    # Source distribution
    src_rows = await db.execute(
        select(RawFeedback.source, func.count(RawFeedback.id)).group_by(RawFeedback.source)
    )
    source_dist = {r[0]: r[1] for r in src_rows.fetchall()}

    # Processing success rate (last 24h)
    since = now - timedelta(days=7)
    total_runs = (
        await db.execute(
            select(func.count(AgentRun.id)).where(AgentRun.started_at >= since)
        )
    ).scalar() or 1
    success_runs = (
        await db.execute(
            select(func.count(AgentRun.id)).where(
                AgentRun.started_at >= since, AgentRun.status == "success"
            )
        )
    ).scalar() or 0
    success_rate = round(success_runs / max(total_runs, 1), 3)

    # Avg agent latency
    avg_lat = (
        await db.execute(
            select(func.avg(AgentRun.latency_ms)).where(AgentRun.started_at >= since)
        )
    ).scalar() or 0.0

    # Token usage & cost
    token_stats = await db.execute(
        select(AgentRun.tokens_used, AgentRun.output_data).where(AgentRun.tokens_used > 0)
    )
    
    total_tokens = 0
    total_cost = 0.0
    for row in token_stats:
        tokens = row[0] or 0
        total_tokens += tokens
        
        # Calculate cost breakdown
        usage = row[1] or {}
        # Since we just started storing JSON, older records might not have prompt_tokens
        prompt_tokens = usage.get("prompt_tokens", tokens * 0.8)
        comp_tokens = usage.get("completion_tokens", tokens * 0.2)
        
        total_cost += (prompt_tokens / 1_000_000) * settings.GEMINI_COST_INPUT_1M
        total_cost += (comp_tokens / 1_000_000) * settings.GEMINI_COST_OUTPUT_1M

    return AnalyticsOverview(
        total_feedback=total,
        processed_today=processed_today,
        pending_review=pending_review,
        open_tickets=open_tickets,
        avg_confidence=round(float(avg_conf), 3),
        category_distribution=category_dist,
        priority_distribution=priority_dist,
        sentiment_distribution=sentiment_dist,
        source_distribution=source_dist,
        processing_success_rate=success_rate,
        avg_agent_latency_ms=round(float(avg_lat), 2),
        total_tokens=total_tokens,
        total_cost_usd=round(total_cost, 4),
    )


@router.get("/trends", response_model=List[TrendPoint])
async def get_trends(
    days: int = Query(14, ge=1, le=90),
    group_by: str = Query("category", regex="^(category|sentiment|priority)$"),
    db: AsyncSession = Depends(get_db),
):
    """Daily trend data grouped by category/sentiment/priority."""
    since = datetime.utcnow() - timedelta(days=days)

    # Build date-truncated query
    date_col = func.date_trunc("day", ProcessedFeedback.processed_at).label("day")
    group_col = getattr(ProcessedFeedback, group_by)

    rows = await db.execute(
        select(date_col, group_col, func.count(ProcessedFeedback.id))
        .where(ProcessedFeedback.processed_at >= since)
        .group_by("day", group_col)
        .order_by("day")
    )

    return [
        TrendPoint(
            date=r[0].strftime("%Y-%m-%d") if r[0] else "",
            count=r[2],
            **{group_by: r[1]},
        )
        for r in rows.fetchall()
    ]


@router.get("/top-issues")
async def get_top_issues(
    limit: int = Query(10, le=50),
    db: AsyncSession = Depends(get_db),
):
    """Most common issues by category and key phrases."""
    rows = await db.execute(
        select(ProcessedFeedback.category, func.count(ProcessedFeedback.id).label("count"))
        .where(ProcessedFeedback.category.in_(["Bug", "Complaint"]))
        .group_by(ProcessedFeedback.category)
        .order_by(func.count(ProcessedFeedback.id).desc())
        .limit(limit)
    )
    return [{"category": r[0], "count": r[1]} for r in rows.fetchall()]


@router.get("/duplicates")
async def get_duplicates(
    limit: int = Query(20, le=100),
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
):
    """Show duplicate and near-duplicate feedback groups."""
    from db.models import RawFeedback
    from sqlalchemy.orm import aliased

    RawA = aliased(RawFeedback)
    
    base_cond = (
        (ProcessedFeedback.is_duplicate == True) |  # noqa: E712
        (ProcessedFeedback.similarity_score >= 0.6)
    )

    count_q = select(func.count()).select_from(ProcessedFeedback).where(base_cond)
    total = await db.scalar(count_q)

    rows = await db.execute(
        select(ProcessedFeedback)
        .where(base_cond)
        .order_by(ProcessedFeedback.similarity_score.desc())
        .limit(limit).offset(offset)
    )
    dupes = rows.scalars().all()

    # Fetch the raw text for each dupe and its original
    result = []
    for d in dupes:
        # Get text for this item
        raw_row = await db.execute(
            select(RawFeedback.title, RawFeedback.body).where(RawFeedback.id == d.raw_id)
        )
        raw = raw_row.first()
        this_text = (raw.title or raw.body or "")[:100] if raw else ""

        # Get text for the original it duplicates (if any)
        orig_text = None
        if d.duplicate_of_id:
            orig_pf = await db.execute(
                select(ProcessedFeedback.raw_id).where(ProcessedFeedback.id == d.duplicate_of_id)
            )
            orig_pf_row = orig_pf.first()
            if orig_pf_row:
                orig_raw = await db.execute(
                    select(RawFeedback.title, RawFeedback.body).where(RawFeedback.id == orig_pf_row.raw_id)
                )
                orig_raw_row = orig_raw.first()
                if orig_raw_row:
                    orig_text = (orig_raw_row.title or orig_raw_row.body or "")[:100]

        result.append({
            "id": d.id,
            "duplicate_of_id": d.duplicate_of_id,
            "similarity_score": d.similarity_score,
            "category": d.category,
            "processed_at": d.processed_at.isoformat(),
            "text": this_text,
            "original_text": orig_text,
        })
    
    return {
        "items": result,
        "total": total
    }
