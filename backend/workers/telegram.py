"""
Telegram Notification Service — sends structured alerts after each scheduler cycle.
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional

import httpx

from core.config import settings

logger = logging.getLogger(__name__)

_TELEGRAM_API = "https://api.telegram.org"


def _is_configured() -> bool:
    return bool(settings.TELEGRAM_BOT_TOKEN and settings.TELEGRAM_CHAT_ID)


async def send_telegram(message: str) -> bool:
    """Send a plain-text message via Telegram Bot API. Returns True on success."""
    if not _is_configured():
        logger.debug("Telegram not configured — skipping notification")
        return False

    url = f"{_TELEGRAM_API}/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": settings.TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            logger.info("Telegram notification sent successfully")
            return True
    except Exception as exc:
        logger.error("Telegram notification failed: %s", exc)
        return False


async def notify_cycle_success(
    *,
    fetched: int,
    new_ingested: int,
    processed: int,
    cycle_number: int,
    elapsed_seconds: float,
) -> bool:
    """Send a success notification after a completed ingestion cycle."""
    ts = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    msg = (
        "✅ <b>Ingestion Cycle #{cycle} — Success</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "📥 Fetched: <b>{fetched}</b>\n"
        "🆕 New ingested: <b>{new}</b>\n"
        "🤖 AI processed: <b>{processed}</b>\n"
        "⏱ Duration: <b>{elapsed:.1f}s</b>\n"
        "🕐 Timestamp: <code>{ts}</code>\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "💡 Next cycle in {interval} minutes."
    ).format(
        cycle=cycle_number,
        fetched=fetched,
        new=new_ingested,
        processed=processed,
        elapsed=elapsed_seconds,
        ts=ts,
        interval=settings.INGESTION_INTERVAL_MINUTES,
    )
    return await send_telegram(msg)


async def notify_cycle_failure(
    *,
    cycle_number: int,
    error: str,
    source: Optional[str] = None,
) -> bool:
    """Send a failure notification when a cycle encounters an error."""
    ts = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    source_line = f"\n📌 Source: <b>{source}</b>" if source else ""
    msg = (
        "❌ <b>Ingestion Cycle #{cycle} — Failed</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━{source_line}\n"
        "🐛 Error: <code>{error}</code>\n"
        "🕐 Timestamp: <code>{ts}</code>\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "⚠ The scheduler will retry in {interval} minutes."
    ).format(
        cycle=cycle_number,
        source_line=source_line,
        error=error[:300],
        ts=ts,
        interval=settings.INGESTION_INTERVAL_MINUTES,
    )
    return await send_telegram(msg)


async def notify_no_new_data(
    *,
    fetched: int,
    cycle_number: int,
) -> bool:
    """Send notification when a cycle completes but no new reviews were found."""
    ts = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    msg = (
        "ℹ️ <b>Ingestion Cycle #{cycle} — No New Reviews</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "📥 Checked: <b>{fetched}</b> reviews\n"
        "🆕 New: <b>0</b> (No New Reviews available)\n"
        "🤖 Processed: <b>0</b>\n"
        "🕐 Timestamp: <code>{ts}</code>\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "💤 No action needed. Will check again in {interval} minutes."
    ).format(
        cycle=cycle_number,
        fetched=fetched,
        ts=ts,
        interval=settings.INGESTION_INTERVAL_MINUTES,
    )
    return await send_telegram(msg)


async def notify_scheduler_started() -> bool:
    """Notify when the scheduler starts."""
    ts = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    ttl = settings.SCHEDULER_MAX_RUNTIME_MINUTES
    ttl_line = f"⏳ Auto-stop: after <b>{ttl} minutes</b>" if ttl > 0 else "⏳ Mode: <b>continuous (no auto-stop)</b>"
    msg = (
        "🚀 <b>Scheduler Started</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "📋 Interval: every <b>{interval} minutes</b>\n"
        "{ttl_line}\n"
        "🕐 Started at: <code>{ts}</code>\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "Feedback processing is now active."
    ).format(interval=settings.INGESTION_INTERVAL_MINUTES, ttl_line=ttl_line, ts=ts)
    return await send_telegram(msg)


async def notify_scheduler_stopped(*, total_cycles: int, reason: str = "TTL expired") -> bool:
    """Notify when the scheduler stops."""
    ts = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    msg = (
        "🛑 <b>Scheduler Stopped</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "📊 Total cycles completed: <b>{cycles}</b>\n"
        "📌 Reason: <b>{reason}</b>\n"
        "🕐 Stopped at: <code>{ts}</code>"
    ).format(cycles=total_cycles, reason=reason, ts=ts)
    return await send_telegram(msg)
