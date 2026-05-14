"""
Ingestion Agent — Fetches feedback from external sources (GitHub, Reddit, Manual).
"""
from __future__ import annotations

import asyncio
import hashlib
import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

import httpx

from core.config import settings
from db.database import AsyncSessionLocal
from db.models import RawFeedback
from sqlalchemy import select

logger = logging.getLogger(__name__)


def _make_external_id(source: str, raw_id: Any) -> str:
    return hashlib.sha256(f"{source}:{raw_id}".encode()).hexdigest()[:32]


async def _exists(external_id: str) -> bool:
    """Check if feedback already ingested."""
    from sqlalchemy import select

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(RawFeedback.id).where(RawFeedback.external_id == external_id).limit(1)
        )
        return result.scalar() is not None


async def _save(records: List[Dict]) -> int:
    """Save new feedback records, skipping duplicates. Returns count saved."""
    from sqlalchemy import select

    saved = 0
    async with AsyncSessionLocal() as session:
        for rec in records:
            ext_id = rec["external_id"]
            exists = await session.execute(
                select(RawFeedback.id).where(RawFeedback.external_id == ext_id).limit(1)
            )
            if exists.scalar():
                continue

            session.add(RawFeedback(
                id=str(uuid.uuid4()),
                external_id=ext_id,
                source=rec["source"],
                source_url=rec.get("source_url"),
                title=rec.get("title"),
                body=rec["body"],
                author=rec.get("author"),
                raw_metadata=rec.get("raw_metadata", {}),
                ingested_at=datetime.utcnow(),
                processed=False,
                processing_status="pending",
            ))
            saved += 1

        await session.commit()
    return saved


async def ingest_github_issues(limit: int = 30) -> Dict[str, int]:
    if not settings.GITHUB_TOKEN or not settings.GITHUB_REPO_OWNER:
        logger.info("GitHub ingestion skipped — not configured")
        return {"fetched": 0, "new": 0}

    url = (
        f"https://api.github.com/repos/{settings.GITHUB_REPO_OWNER}"
        f"/{settings.GITHUB_REPO_NAME}/issues"
    )
    headers = {
        "Authorization": f"Bearer {settings.GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json",
    }
    params = {"state": "open", "per_page": limit, "sort": "updated"}

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(url, headers=headers, params=params)
            resp.raise_for_status()
            issues = resp.json()

        records = []
        for issue in issues:
            if issue.get("pull_request"):
                continue 
            ext_id = _make_external_id("github", issue["id"])
            records.append({
                "external_id": ext_id,
                "source": "github",
                "source_url": issue.get("html_url"),
                "title": issue.get("title", ""),
                "body": issue.get("body") or issue.get("title", ""),
                "author": issue.get("user", {}).get("login"),
                "raw_metadata": {
                    "github_id": issue["id"],
                    "number": issue["number"],
                    "labels": [l["name"] for l in issue.get("labels", [])],
                    "state": issue.get("state"),
                    "created_at": issue.get("created_at"),
                },
            })

        new = await _save(records)
        logger.info("GitHub: fetched=%d new=%d", len(records), new)
        return {"fetched": len(records), "new": new}

    except Exception as exc:
        logger.error("GitHub ingestion error: %s", exc)
        return {"fetched": 0, "new": 0, "error": str(exc)}


async def ingest_reddit(subreddits: Optional[List[str]] = None, limit: int = 25) -> Dict[str, int]:
    if not settings.REDDIT_CLIENT_ID:
        logger.info("Reddit ingestion skipped — not configured")
        return {"fetched": 0, "new": 0}

    targets = subreddits or settings.REDDIT_SUBREDDITS
    total_fetched = 0
    total_new = 0

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            token_resp = await client.post(
                "https://www.reddit.com/api/v1/access_token",
                data={"grant_type": "client_credentials"},
                auth=(settings.REDDIT_CLIENT_ID, settings.REDDIT_CLIENT_SECRET or ""),
                headers={"User-Agent": settings.REDDIT_USER_AGENT},
            )
            token_resp.raise_for_status()
            token = token_resp.json()["access_token"]

            for subreddit in targets:
                resp = await client.get(
                    f"https://oauth.reddit.com/r/{subreddit}/new",
                    headers={
                        "Authorization": f"Bearer {token}",
                        "User-Agent": settings.REDDIT_USER_AGENT,
                    },
                    params={"limit": limit},
                )
                resp.raise_for_status()
                posts = resp.json()["data"]["children"]

                records = []
                for post in posts:
                    d = post["data"]
                    body = d.get("selftext", "") or d.get("title", "")
                    if len(body) < 10:
                        continue
                    ext_id = _make_external_id("reddit", d["id"])
                    records.append({
                        "external_id": ext_id,
                        "source": "reddit",
                        "source_url": f"https://reddit.com{d.get('permalink', '')}",
                        "title": d.get("title", "")[:500],
                        "body": body[:5000],
                        "author": d.get("author"),
                        "raw_metadata": {
                            "reddit_id": d["id"],
                            "subreddit": subreddit,
                            "score": d.get("score"),
                            "num_comments": d.get("num_comments"),
                            "created_utc": d.get("created_utc"),
                        },
                    })

                new = await _save(records)
                total_fetched += len(records)
                total_new += new
                logger.info("Reddit r/%s: fetched=%d new=%d", subreddit, len(records), new)

    except Exception as exc:
        logger.error("Reddit ingestion error: %s", exc)
        return {"fetched": total_fetched, "new": total_new, "error": str(exc)}

    return {"fetched": total_fetched, "new": total_new}


async def ingest_google_play_reviews() -> Dict[str, int]:
    if not settings.GOOGLE_PLAY_APP_ID:
        logger.info("Google Play ingestion skipped — not configured")
        return {"fetched": 0, "new": 0}

    app_id = settings.GOOGLE_PLAY_APP_ID
    count = settings.GOOGLE_PLAY_REVIEW_COUNT

    try:
        import asyncio
        from google_play_scraper import reviews, Sort

        loop = asyncio.get_event_loop()
        result, _ = await loop.run_in_executor(
            None,
            lambda: reviews(
                app_id,
                lang="en",
                country="us",
                sort=Sort.NEWEST,
                count=count,
            ),
        )

        records = []
        for review in result:
            review_id = review.get("reviewId", "")
            body = review.get("content", "").strip()
            if not body:
                continue
            ext_id = _make_external_id("googleplay", review_id)
            records.append({
                "external_id": ext_id,
                "source": "google_play",
                "source_url": f"https://play.google.com/store/apps/details?id={app_id}",
                "title": None,
                "body": body[:5000],
                "author": review.get("userName"),
                "raw_metadata": {
                    "review_id": review_id,
                    "app_id": app_id,
                    "score": review.get("score"),
                    "thumbs_up_count": review.get("thumbsUpCount"),
                    "review_created_version": review.get("reviewCreatedVersion"),
                    "at": review.get("at").isoformat() if review.get("at") else None,
                },
            })

        new = await _save(records)
        logger.info("Google Play (%s): fetched=%d new=%d", app_id, len(records), new)
        return {"fetched": len(records), "new": new}

    except Exception as exc:
        logger.error("Google Play ingestion error: %s", exc)
        return {"fetched": 0, "new": 0, "error": str(exc)}


async def ingest_manual(
    text: str,
    title: Optional[str] = None,
    author: Optional[str] = None,
    metadata: Optional[Dict] = None,
) -> RawFeedback:
    """Ingest a single feedback record submitted via API or UI."""
    import hashlib
    ext_id = hashlib.sha256(f"manual:{text[:100]}:{datetime.utcnow().isoformat()}".encode()).hexdigest()[:32]

    async with AsyncSessionLocal() as session:
        feedback = RawFeedback(
            id=str(uuid.uuid4()),
            external_id=ext_id,
            source="manual",
            title=title,
            body=text,
            author=author,
            raw_metadata=metadata or {},
            ingested_at=datetime.utcnow(),
            processed=False,
            processing_status="pending",
        )
        session.add(feedback)
        await session.commit()
        await session.refresh(feedback)
        return feedback


async def process_pending_feedback(batch_size: int = None) -> int:
    """
    Run the AI pipeline for any unprocessed feedback records.
    """
    from db.database import AsyncSessionLocal
    from db.models import RawFeedback
    import asyncio

    if batch_size is None:
        from core.config import settings
        batch_size = settings.MAX_INGESTION_BATCH

    logger.info("--- [Queue] Checking for pending feedback to process (batch_size=%d) ---", batch_size)

    from sqlalchemy import select
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(RawFeedback.id)
            .where(RawFeedback.processed == False)
            .where(RawFeedback.processing_status == "pending")
            .limit(batch_size)
        )
        pending_ids = result.scalars().all()

    if not pending_ids:
        logger.info("--- [Queue] No pending feedback found ---")
        return 0

    logger.info("--- [Queue] Starting AI processing for %d items ---", len(pending_ids))

    try:
        logger.info("--- [DEBUG] Importing Orchestrator... ---")
        from agents.orchestrator import get_orchestrator
        logger.info("--- [DEBUG] Orchestrator imported. Initializing brain... ---")
        orchestrator = get_orchestrator()
        logger.info("--- [DEBUG] Brain initialized. Setting up workers... ---")
        semaphore = asyncio.Semaphore(10)
        processed_count = 0
    except Exception as e:
        logger.error("!!! [DEBUG] FAILED to initialize orchestrator: %s", e)
        return 0

    async def _process_one(fb_id: str) -> bool:
        async with semaphore:
            try:
                logger.info("--- [Queue] Locking item %s for processing ---", fb_id)
                from sqlalchemy import select
                async with AsyncSessionLocal() as session:
                    res = await session.execute(select(RawFeedback).where(RawFeedback.id == fb_id))
                    feedback = res.scalar_one_or_none()
                    if not feedback:
                        return False
                    feedback.processing_status = "processing"
                    await session.commit()
                
                await orchestrator.process_by_id(fb_id)
                return True
            except Exception as exc:
                logger.error("!!! [Queue] Error processing feedback %s: %s", fb_id, exc)
                return False

    results = await asyncio.gather(*[_process_one(fid) for fid in pending_ids])
    processed_count = sum(1 for r in results if r)

    logger.info("Processed %d/%d pending feedback records", processed_count, len(pending_ids))
    return processed_count
