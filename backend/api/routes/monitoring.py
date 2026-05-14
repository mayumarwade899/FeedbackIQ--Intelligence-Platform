"""Monitoring, agent status, and ingestion trigger endpoints."""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.schemas import AgentRunResponse, MonitoringMetrics
from core.config import settings
from db.database import get_db
from db.models import AgentRun, IngestionRun

router = APIRouter()


@router.get("/metrics", response_model=MonitoringMetrics)
async def get_monitoring_metrics(db: AsyncSession = Depends(get_db)):
    since = datetime.utcnow() - timedelta(days=7)

    agent_rows = await db.execute(
        select(
            AgentRun.agent_name,
            AgentRun.status,
            func.avg(AgentRun.latency_ms).label("avg_lat"),
            func.count(AgentRun.id).label("cnt"),
        )
        .where(AgentRun.started_at >= since)
        .group_by(AgentRun.agent_name, AgentRun.status)
    )
    rows = agent_rows.fetchall()

    agent_success: dict = {}
    agent_latency: dict = {}
    agent_totals: dict = {}

    for row in rows:
        name, status, avg_lat, cnt = row
        if name not in agent_totals:
            agent_totals[name] = 0
            agent_success[name] = 0
            agent_latency[name] = 0.0
        agent_totals[name] += cnt
        if status == "success":
            agent_success[name] += cnt
            agent_latency[name] = round(float(avg_lat or 0), 2)

    agent_success_rate = {
        name: round(agent_success.get(name, 0) / max(total, 1), 3)
        for name, total in agent_totals.items()
    }
    agent_avg_latency = {name: agent_latency.get(name, 0.0) for name in agent_totals}

    total_runs = (
        await db.execute(
            select(func.count(AgentRun.id)).where(AgentRun.started_at >= since)
        )
    ).scalar() or 0

    failed_runs = (
        await db.execute(
            select(func.count(AgentRun.id)).where(
                AgentRun.started_at >= since, AgentRun.status == "failed"
            )
        )
    ).scalar() or 0

    throughput = round(total_runs / 24, 2)

    last_ing = await db.execute(
        select(IngestionRun.completed_at)
        .where(IngestionRun.status == "completed")
        .order_by(IngestionRun.completed_at.desc())
        .limit(1)
    )
    last_ingestion = last_ing.scalar()

    src_rows = await db.execute(
        select(IngestionRun.source, func.sum(IngestionRun.items_new))
        .where(IngestionRun.started_at >= since)
        .group_by(IngestionRun.source)
    )
    ingestion_sources = {r[0]: int(r[1] or 0) for r in src_rows.fetchall()}

    token_rows = await db.execute(
        select(AgentRun.tokens_used, AgentRun.output_data)
        .where(AgentRun.started_at >= since, AgentRun.tokens_used > 0)
    )
    
    total_tokens_24h = 0
    total_cost_24h = 0.0
    for tokens, usage in token_rows.fetchall():
        total_tokens_24h += tokens or 0
        usage = usage or {}
        prompt = usage.get("prompt_tokens", (tokens or 0) * 0.8)
        comp = usage.get("completion_tokens", (tokens or 0) * 0.2)
        total_cost_24h += (prompt / 1_000_000) * settings.GEMINI_COST_INPUT_1M
        total_cost_24h += (comp / 1_000_000) * settings.GEMINI_COST_OUTPUT_1M

    return MonitoringMetrics(
        agent_success_rate=agent_success_rate,
        agent_avg_latency=agent_avg_latency,
        total_runs_24h=total_runs,
        failed_runs_24h=failed_runs,
        throughput_per_hour=throughput,
        last_ingestion=last_ingestion,
        ingestion_sources=ingestion_sources,
        total_tokens_24h=total_tokens_24h,
        total_cost_24h_usd=round(total_cost_24h, 4),
    )


@router.get("/agent-runs", response_model=List[AgentRunResponse])
async def list_agent_runs(
    agent_name: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = Query(50, le=200),
    db: AsyncSession = Depends(get_db),
):
    q = select(AgentRun).order_by(AgentRun.started_at.desc())
    if agent_name:
        q = q.where(AgentRun.agent_name == agent_name)
    if status:
        q = q.where(AgentRun.status == status)
    q = q.limit(limit)
    result = await db.execute(q)
    return [
        AgentRunResponse(
            id=r.id, agent_name=r.agent_name, status=r.status,
            latency_ms=r.latency_ms, tokens_used=r.tokens_used,
            estimated_cost=round(
                ((r.output_data or {}).get("prompt_tokens", (r.tokens_used or 0) * 0.8) / 1_000_000 * settings.GEMINI_COST_INPUT_1M) +
                ((r.output_data or {}).get("completion_tokens", (r.tokens_used or 0) * 0.2) / 1_000_000 * settings.GEMINI_COST_OUTPUT_1M),
                6
            ) if r.tokens_used else 0.0,
            error_message=r.error_message, started_at=r.started_at,
            completed_at=r.completed_at,
        )
        for r in result.scalars().all()
    ]
