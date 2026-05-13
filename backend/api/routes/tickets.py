"""Ticket management endpoints."""
from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.schemas import TicketResponse, TicketUpdate, PaginatedResponse
from db.database import get_db
from db.models import Ticket

router = APIRouter()


def _serialize(t: Ticket) -> TicketResponse:
    return TicketResponse(
        id=t.id, ticket_number=t.ticket_number, feedback_id=t.feedback_id,
        title=t.title, description=t.description, category=t.category,
        priority=t.priority, status=t.status, impact_summary=t.impact_summary,
        suggested_resolution=t.suggested_resolution, labels=t.labels,
        github_issue_number=t.github_issue_number,
        github_issue_url=t.github_issue_url,
        github_synced=t.github_synced,
        created_at=t.created_at, updated_at=t.updated_at,
    )


@router.get("", response_model=PaginatedResponse[TicketResponse])
async def list_tickets(
    status: Optional[str] = None,
    priority: Optional[str] = None,
    category: Optional[str] = None,
    limit: int = Query(50, le=200),
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
):
    from sqlalchemy import func
    q = select(Ticket).order_by(Ticket.created_at.desc())
    count_q = select(func.count()).select_from(Ticket)

    if status:
        q = q.where(Ticket.status == status)
        count_q = count_q.where(Ticket.status == status)
    if priority:
        q = q.where(Ticket.priority == priority)
        count_q = count_q.where(Ticket.priority == priority)
    if category:
        q = q.where(Ticket.category == category)
        count_q = count_q.where(Ticket.category == category)
    
    total = await db.scalar(count_q)
    
    q = q.limit(limit).offset(offset)
    result = await db.execute(q)
    
    return {
        "items": [_serialize(t) for t in result.scalars().all()],
        "total": total
    }


@router.get("/{ticket_id}", response_model=TicketResponse)
async def get_ticket(ticket_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Ticket).where(Ticket.id == ticket_id))
    ticket = result.scalar_one_or_none()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return _serialize(ticket)


@router.patch("/{ticket_id}", response_model=TicketResponse)
async def update_ticket(
    ticket_id: str,
    update: TicketUpdate,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Ticket).where(Ticket.id == ticket_id))
    ticket = result.scalar_one_or_none()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    for field, value in update.model_dump(exclude_none=True).items():
        setattr(ticket, field, value)

    await db.commit()
    await db.refresh(ticket)
    return _serialize(ticket)


@router.post("/{ticket_id}/sync-github")
async def sync_to_github(ticket_id: str, db: AsyncSession = Depends(get_db)):
    """Push ticket to GitHub Issues."""
    from core.config import settings

    if not settings.GITHUB_TOKEN:
        raise HTTPException(status_code=400, detail="GitHub not configured")

    result = await db.execute(select(Ticket).where(Ticket.id == ticket_id))
    ticket = result.scalar_one_or_none()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    import httpx

    url = (
        f"https://api.github.com/repos/{settings.GITHUB_REPO_OWNER}"
        f"/{settings.GITHUB_REPO_NAME}/issues"
    )
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(
            url,
            json={
                "title": ticket.title,
                "body": ticket.description,
                "labels": ticket.labels or [],
            },
            headers={
                "Authorization": f"Bearer {settings.GITHUB_TOKEN}",
                "Accept": "application/vnd.github.v3+json",
            },
        )
        resp.raise_for_status()
        issue = resp.json()

    ticket.github_issue_number = issue["number"]
    ticket.github_issue_url = issue["html_url"]
    ticket.github_synced = True
    await db.commit()

    return {"github_issue_number": issue["number"], "github_issue_url": issue["html_url"]}
