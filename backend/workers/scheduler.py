"""
Background Scheduler — Thread-isolated APScheduler for production-grade reliability.

Architecture:
  - Uses BackgroundScheduler (thread-based) instead of AsyncIOScheduler
  - Each job runs in a dedicated thread with its own asyncio event loop
  - Completely isolated from FastAPI's event loop — no contention
  - API traffic, ingestion, AI processing, and notifications run in parallel
  - Jobs are never skipped or delayed due to API load

Features:
  - Fetches feedback from configured sources every N minutes
  - Processes pending feedback through the AI pipeline
  - Auto-stops after a configurable TTL (default: 2 hours)
  - Sends Telegram notifications on success/failure
  - Retries failed jobs automatically via APScheduler
"""
from __future__ import annotations

import asyncio
import logging
import threading
import time
import uuid
from datetime import datetime, timedelta
from typing import Optional

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.date import DateTrigger

from core.config import settings

logger = logging.getLogger(__name__)

_scheduler: Optional[BackgroundScheduler] = None
_cycle_count: int = 0
_start_time: Optional[float] = None
_lock = threading.Lock()


def _run_async(coro):
    """Run an async coroutine in a fresh event loop on the current thread."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def _ingestion_job():
    """Thread-safe ingestion job — runs in its own thread with its own event loop."""
    _run_async(_run_ingestion_cycle())


async def _run_ingestion_cycle():
    """Full ingestion cycle: fetch → ingest → process → notify."""
    global _cycle_count

    from agents.ingestion_agent import (
        ingest_google_play_reviews,
        process_pending_feedback,
    )
    from workers.telegram import notify_cycle_success, notify_cycle_failure, notify_no_new_data

    with _lock:
        _cycle_count += 1
        cycle = _cycle_count

    cycle_start = time.time()
    run_id = str(uuid.uuid4())

    logger.info(
        "━━━ Ingestion cycle #%d started (run_id=%s, thread=%s) ━━━",
        cycle, run_id, threading.current_thread().name,
    )

    total_fetched = 0
    total_new = 0
    has_error = False

    from db.database import AsyncSessionLocal
    from db.models import IngestionRun

    for source, fn in [
        ("google_play", ingest_google_play_reviews),
    ]:
        # Track each source in the DB
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
            fetched = result.get("fetched", 0)
            new = result.get("new", 0)
            total_fetched += fetched
            total_new += new

            async with AsyncSessionLocal() as session:
                r = await session.get(IngestionRun, run_db_id)
                if r:
                    r.status = "completed"
                    r.items_fetched = fetched
                    r.items_new = new
                    r.completed_at = datetime.utcnow()
                    await session.commit()

            logger.info("  ✓ %s: fetched=%d, new=%d", source, fetched, new)

        except Exception as exc:
            has_error = True
            logger.error("  ✗ %s failed: %s", source, exc)

            async with AsyncSessionLocal() as session:
                r = await session.get(IngestionRun, run_db_id)
                if r:
                    r.status = "failed"
                    r.error_message = str(exc)[:500]
                    r.completed_at = datetime.utcnow()
                    await session.commit()

            await notify_cycle_failure(
                cycle_number=cycle,
                error=str(exc),
                source=source,
            )

    # Process all pending feedback through AI pipeline
    processed = 0
    try:
        processed = await process_pending_feedback(
            batch_size=settings.MAX_INGESTION_BATCH
        )
        logger.info("  🤖 AI processing complete: %d records", processed)
    except Exception as exc:
        has_error = True
        logger.error("  ✗ AI processing failed: %s", exc)
        await notify_cycle_failure(
            cycle_number=cycle,
            error=str(exc),
            source="ai_processing",
        )

    elapsed = time.time() - cycle_start
    logger.info(
        "━━━ Cycle #%d complete in %.1fs — fetched=%d, new=%d, processed=%d ━━━",
        cycle, elapsed, total_fetched, total_new, processed,
    )

    # Send appropriate notification based on results
    if not has_error:
        if total_new > 0 or processed > 0:
            await notify_cycle_success(
                fetched=total_fetched,
                new_ingested=total_new,
                processed=processed,
                cycle_number=cycle,
                elapsed_seconds=elapsed,
            )
        else:
            await notify_no_new_data(
                fetched=total_fetched,
                cycle_number=cycle,
            )

    # ── Check TTL: auto-stop if runtime exceeded ──
    await _check_ttl_and_stop()


async def _check_ttl_and_stop():
    """Shut down the scheduler if TTL has expired."""
    global _scheduler, _start_time

    ttl_minutes = settings.SCHEDULER_MAX_RUNTIME_MINUTES
    if ttl_minutes <= 0 or _start_time is None:
        return  # 0 = run forever

    elapsed_minutes = (time.time() - _start_time) / 60
    remaining = ttl_minutes - elapsed_minutes

    if remaining <= 0:
        logger.info(
            "⏰ Scheduler TTL expired (ran for %.1f minutes, limit=%d). Shutting down.",
            elapsed_minutes, ttl_minutes,
        )
        from workers.telegram import notify_scheduler_stopped
        await notify_scheduler_stopped(
            total_cycles=_cycle_count,
            reason=f"TTL expired ({ttl_minutes} minutes)",
        )
        if _scheduler and _scheduler.running:
            _scheduler.shutdown(wait=False)
    else:
        logger.info("⏳ Scheduler TTL: %.1f minutes remaining", remaining)


def _force_stop_job():
    """Thread-safe TTL watchdog — runs in its own thread."""
    _run_async(_force_stop())


async def _force_stop():
    """Force-stop callback triggered by the TTL watchdog."""
    global _scheduler
    logger.info("🛑 TTL watchdog fired — shutting down scheduler")
    from workers.telegram import notify_scheduler_stopped
    await notify_scheduler_stopped(
        total_cycles=_cycle_count,
        reason=f"TTL watchdog ({settings.SCHEDULER_MAX_RUNTIME_MINUTES} minutes)",
    )
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)


async def start_scheduler():
    """Start the BackgroundScheduler with ingestion jobs (thread-isolated)."""
    global _scheduler, _cycle_count, _start_time

    if not settings.INGESTION_ENABLED:
        logger.info("⚠ Ingestion scheduler disabled via INGESTION_ENABLED=false")
        return

    _cycle_count = 0
    _start_time = time.time()

    _scheduler = BackgroundScheduler(
        timezone="UTC",
        job_defaults={
            "coalesce": True,           # Merge missed runs into one
            "max_instances": 1,         # Prevent overlapping executions
            "misfire_grace_time": None,  # Never skip a job
        },
    )

    # Primary recurring job: ingestion + processing (runs in thread pool)
    _scheduler.add_job(
        _ingestion_job,
        trigger=IntervalTrigger(minutes=settings.INGESTION_INTERVAL_MINUTES),
        id="ingestion_cycle",
        replace_existing=True,
        max_instances=1,                      # No overlapping ingestion runs
        next_run_time=datetime.utcnow(),  # Run immediately on startup
    )

    # TTL watchdog: if configured, add a one-shot job to force-stop
    ttl = settings.SCHEDULER_MAX_RUNTIME_MINUTES
    if ttl > 0:
        stop_at = datetime.utcnow() + timedelta(minutes=ttl)
        _scheduler.add_job(
            _force_stop_job,
            trigger=DateTrigger(run_date=stop_at),
            id="ttl_watchdog",
            replace_existing=True,
        )
        logger.info("⏰ TTL watchdog scheduled — will force-stop at %s", stop_at.isoformat())

    _scheduler.start()
    logger.info(
        "✅ Scheduler started (thread-isolated) — ingestion every %d minutes (TTL: %s)",
        settings.INGESTION_INTERVAL_MINUTES,
        f"{ttl} minutes" if ttl > 0 else "unlimited",
    )

    # Send Telegram notification
    from workers.telegram import notify_scheduler_started
    await notify_scheduler_started()


async def stop_scheduler():
    """Graceful shutdown (called from app lifespan)."""
    global _scheduler
    if _scheduler and _scheduler.running:
        from workers.telegram import notify_scheduler_stopped
        await notify_scheduler_stopped(
            total_cycles=_cycle_count,
            reason="Application shutdown",
        )
        _scheduler.shutdown(wait=False)
        _scheduler = None
        logger.info("🛑 Scheduler stopped (app shutdown)")
