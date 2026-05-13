"""
Background Scheduler — APScheduler-based continuous ingestion and processing.
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime
from typing import Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from core.config import settings
from db.database import AsyncSessionLocal
from db.models import IngestionRun

logger = logging.getLogger(__name__)

_scheduler: Optional[AsyncIOScheduler] = None


async def _run_ingestion_cycle():
    """Full ingestion cycle: fetch from all sources, then process pending."""
    from agents.ingestion_agent import (
        ingest_github_issues,
        ingest_reddit,
        ingest_google_play_reviews,
        process_pending_feedback,
    )

    run_id = str(uuid.uuid4())
    logger.info("Ingestion cycle started run_id=%s", run_id)

    for source, fn in [
        ("github", ingest_github_issues),
        ("reddit", ingest_reddit),
        ("google_play", ingest_google_play_reviews),
    ]:
        async with AsyncSessionLocal() as session:
            run = IngestionRun(
                id=str(uuid.uuid4()),
                source=source,
                status="running",
                started_at=datetime.utcnow(),
            )
            session.add(run)
            await session.commit()
            run_db_id = run.id

        try:
            result = await fn()
            async with AsyncSessionLocal() as session:
                from sqlalchemy import select
                r = await session.get(IngestionRun, run_db_id)
                if r:
                    r.status = "completed"
                    r.items_fetched = result.get("fetched", 0)
                    r.items_new = result.get("new", 0)
                    r.completed_at = datetime.utcnow()
                    await session.commit()
        except Exception as exc:
            logger.error("Ingestion source=%s failed: %s", source, exc)
            async with AsyncSessionLocal() as session:
                r = await session.get(IngestionRun, run_db_id)
                if r:
                    r.status = "failed"
                    r.error_message = str(exc)[:500]
                    r.completed_at = datetime.utcnow()
                    await session.commit()

    # Process all pending feedback
    processed = await process_pending_feedback(batch_size=settings.MAX_INGESTION_BATCH)
    logger.info("Ingestion cycle complete. Processed %d records.", processed)


async def start_scheduler():
    global _scheduler

    if not settings.INGESTION_ENABLED:
        logger.info("Ingestion scheduler disabled via config")
        return

    _scheduler = AsyncIOScheduler(timezone="UTC")
    _scheduler.add_job(
        _run_ingestion_cycle,
        trigger=IntervalTrigger(minutes=settings.INGESTION_INTERVAL_MINUTES),
        id="ingestion_cycle",
        replace_existing=True,
        max_instances=1,
    )
    _scheduler.start()
    logger.info(
        "Scheduler started — ingestion every %d minutes",
        settings.INGESTION_INTERVAL_MINUTES,
    )


async def stop_scheduler():
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
        logger.info("Scheduler stopped")
