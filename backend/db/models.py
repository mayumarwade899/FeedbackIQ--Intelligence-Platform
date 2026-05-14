"""
SQLAlchemy ORM models for the Feedback Intelligence Platform.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    String, Text, Float, Boolean, DateTime, Integer,
    ForeignKey, JSON, Enum as SAEnum, Index
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from db.database import Base


def gen_uuid() -> str:
    return str(uuid.uuid4())


class RawFeedback(Base):
    """Raw feedback ingested from external sources."""
    __tablename__ = "raw_feedback"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    external_id: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    source: Mapped[str] = mapped_column(String(50), nullable=False)
    source_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    title: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    author: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    raw_metadata: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    ingested_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    processed: Mapped[bool] = mapped_column(Boolean, default=False)
    processing_status: Mapped[str] = mapped_column(String(50), default="pending")

    processed_feedback: Mapped[Optional["ProcessedFeedback"]] = relationship(back_populates="raw")
    processing_runs: Mapped[list["AgentRun"]] = relationship(back_populates="raw_feedback")

    __table_args__ = (
        Index("ix_raw_feedback_source", "source"),
        Index("ix_raw_feedback_processed", "processed"),
        Index("ix_raw_feedback_ingested_at", "ingested_at"),
    )


class ProcessedFeedback(Base):
    """Agent-processed feedback with all enrichments."""
    __tablename__ = "processed_feedback"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    raw_id: Mapped[str] = mapped_column(String(36), ForeignKey("raw_feedback.id"), unique=True)

    category: Mapped[str] = mapped_column(String(50))
    confidence: Mapped[float] = mapped_column(Float)
    priority: Mapped[str] = mapped_column(String(20))

    sentiment: Mapped[str] = mapped_column(String(20))
    sentiment_score: Mapped[float] = mapped_column(Float, default=0.0)
    emotion_tags: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    emotion_intensity: Mapped[float] = mapped_column(Float, default=0.0)
    toxicity_score: Mapped[float] = mapped_column(Float, default=0.0)
    is_abusive: Mapped[bool] = mapped_column(Boolean, default=False)

    language: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    translated_body: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    is_duplicate: Mapped[bool] = mapped_column(Boolean, default=False)
    duplicate_of_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("processed_feedback.id"), nullable=True)
    similarity_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    embedding: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)

    impact_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    suggested_resolution: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    technical_details: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    key_phrases: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)

    review_status: Mapped[str] = mapped_column(String(30), default="pending")
    reviewed_by: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    reviewer_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    processed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    agent_version: Mapped[str] = mapped_column(String(20), default="2.0.0")

    raw: Mapped["RawFeedback"] = relationship(back_populates="processed_feedback")
    ticket: Mapped[Optional["Ticket"]] = relationship(back_populates="feedback")
    duplicate_of: Mapped[Optional["ProcessedFeedback"]] = relationship(
        "ProcessedFeedback", remote_side="ProcessedFeedback.id"
    )

    __table_args__ = (
        Index("ix_processed_category", "category"),
        Index("ix_processed_priority", "priority"),
        Index("ix_processed_sentiment", "sentiment"),
        Index("ix_processed_review_status", "review_status"),
    )


class Ticket(Base):
    """Generated tickets from processed feedback."""
    __tablename__ = "tickets"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    ticket_number: Mapped[str] = mapped_column(String(50), unique=True)
    feedback_id: Mapped[str] = mapped_column(String(36), ForeignKey("processed_feedback.id"))

    title: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(String(50))
    priority: Mapped[str] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(String(30), default="open")
    impact_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    suggested_resolution: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    labels: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)

    github_issue_number: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    github_issue_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    github_synced: Mapped[bool] = mapped_column(Boolean, default=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    feedback: Mapped["ProcessedFeedback"] = relationship(back_populates="ticket")

    __table_args__ = (
        Index("ix_tickets_status", "status"),
        Index("ix_tickets_priority", "priority"),
        Index("ix_tickets_category", "category"),
    )

class AgentRun(Base):
    """Tracks execution of each agent for monitoring/observability."""
    __tablename__ = "agent_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    raw_feedback_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("raw_feedback.id"), nullable=True)
    agent_name: Mapped[str] = mapped_column(String(100))
    status: Mapped[str] = mapped_column(String(20))
    latency_ms: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    tokens_used: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    input_data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    output_data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    langsmith_run_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    raw_feedback: Mapped[Optional["RawFeedback"]] = relationship(back_populates="processing_runs")

    __table_args__ = (
        Index("ix_agent_runs_agent_name", "agent_name"),
        Index("ix_agent_runs_status", "status"),
        Index("ix_agent_runs_started_at", "started_at"),
    )


class IngestionRun(Base):
    """Tracks scheduled ingestion jobs."""
    __tablename__ = "ingestion_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    source: Mapped[str] = mapped_column(String(50))
    status: Mapped[str] = mapped_column(String(20))
    items_fetched: Mapped[int] = mapped_column(Integer, default=0)
    items_new: Mapped[int] = mapped_column(Integer, default=0)
    items_skipped: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
