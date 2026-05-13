"""Manual ingestion trigger endpoints."""
from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks

router = APIRouter()


@router.post("/trigger")
async def trigger_ingestion(background_tasks: BackgroundTasks):
    """Manually trigger a full ingestion cycle."""
    from workers.scheduler import _run_ingestion_cycle
    background_tasks.add_task(_run_ingestion_cycle)
    return {"status": "ingestion_triggered", "message": "Ingestion cycle started in background"}


@router.post("/process-pending")
async def process_pending(background_tasks: BackgroundTasks):
    """Manually trigger processing of pending feedback."""
    from agents.ingestion_agent import process_pending_feedback
    background_tasks.add_task(process_pending_feedback)
    return {"status": "processing_triggered"}


@router.post("/trigger-google-play")
async def trigger_google_play(background_tasks: BackgroundTasks):
    """Manually trigger Google Play Store review ingestion."""
    from agents.ingestion_agent import ingest_google_play_reviews
    from agents.ingestion_agent import process_pending_feedback

    async def _run():
        await ingest_google_play_reviews()
        await process_pending_feedback()

    background_tasks.add_task(_run)
    return {"status": "google_play_ingestion_triggered", "message": "Fetching Google Play reviews in background"}
