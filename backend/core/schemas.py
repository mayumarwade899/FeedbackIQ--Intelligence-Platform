"""
Pydantic schemas and TypedDict state definitions for the agent pipeline.
"""
from __future__ import annotations

import operator
from datetime import datetime
from typing import Annotated, Any, Dict, List, Optional, TypedDict
from pydantic import BaseModel, Field


def _last(current, new):
    """Reducer: always take the newest value (handles parallel branch writes)."""
    return new if new is not None else current


# ── Agent Pipeline State ──────────────────────────────────────────────────────

class AgentState(TypedDict, total=False):
    """Shared state flowing through the LangGraph agent pipeline.

    Scalar fields use _last reducer so parallel branches don't conflict.
    List fields use operator.add so both branches can append safely.
    """
    raw_feedback_id: Annotated[str, _last]
    source: Annotated[str, _last]
    text: Annotated[str, _last]
    title: Annotated[Optional[str], _last]
    metadata: Annotated[Dict[str, Any], _last]

    # Multilingual support
    language: Annotated[str, _last]
    translated_text: Annotated[Optional[str], _last]
    is_english: Annotated[bool, _last]

    # Classification
    category: Annotated[str, _last]
    priority: Annotated[str, _last]
    confidence: Annotated[float, _last]
    classification_rationale: Annotated[str, _last]

    # Sentiment & Toxicity
    sentiment: Annotated[str, _last]
    sentiment_score: Annotated[float, _last]
    emotion_tags: Annotated[List[str], operator.add]
    emotion_intensity: Annotated[float, _last]
    toxicity_score: Annotated[float, _last]
    is_abusive: Annotated[bool, _last]
    masked_text: Annotated[Optional[str], _last]

    # Duplicate detection
    is_duplicate: Annotated[bool, _last]
    duplicate_of_id: Annotated[Optional[str], _last]
    similarity_score: Annotated[Optional[float], _last]
    embedding: Annotated[Optional[List[float]], _last]

    # Insights
    impact_summary: Annotated[str, _last]
    suggested_resolution: Annotated[str, _last]
    key_phrases: Annotated[List[str], operator.add]
    technical_details: Annotated[Dict[str, Any], _last]

    # Generated ticket
    ticket_title: Annotated[str, _last]
    ticket_description: Annotated[str, _last]
    ticket_labels: Annotated[List[str], operator.add]

    # Moderation gate (set by SentimentAgent)
    # skip_processing=True → orchestrator exits after sentiment, no insights/ticket
    skip_processing: Annotated[bool, _last]
    moderation_action: Annotated[str, _last]   # "none" | "masked" | "skipped"

    # Duplicate cluster count — incremented on the representative record each time
    # a semantic duplicate is detected, so the UI shows "N similar reports"
    duplicate_count: Annotated[int, _last]

    # Pipeline tracking
    errors: Annotated[List[str], operator.add]
    agent_traces: Annotated[List[Dict[str, Any]], operator.add]
    processing_start: Annotated[float, _last]
    _last_usage: Annotated[Optional[Any], _last]


# ── API Request/Response Schemas ──────────────────────────────────────────────

class FeedbackSubmit(BaseModel):
    text: str = Field(..., min_length=5, max_length=10000)
    title: Optional[str] = Field(None, max_length=500)
    source: str = Field(default="manual")
    author: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class FeedbackResponse(BaseModel):
    id: str
    external_id: str
    source: str
    title: Optional[str]
    body: str
    author: Optional[str]
    ingested_at: datetime
    processed: bool
    processing_status: str

    class Config:
        from_attributes = True


class ProcessedFeedbackResponse(BaseModel):
    id: str
    raw_id: str
    category: str
    confidence: float
    priority: str
    sentiment: str
    sentiment_score: float
    emotion_tags: Optional[List[str]]
    is_duplicate: bool
    duplicate_of_id: Optional[str]
    impact_summary: Optional[str]
    suggested_resolution: Optional[str]
    key_phrases: Optional[List[str]]
    language: Optional[str]
    translated_body: Optional[str]
    toxicity_score: Optional[float]
    is_abusive: Optional[bool]
    emotion_intensity: Optional[float]
    review_status: str
    reviewed_by: Optional[str]
    reviewed_at: Optional[datetime]
    reviewer_notes: Optional[str]
    processed_at: datetime

    # Nested raw feedback
    raw: Optional[FeedbackResponse] = None

    class Config:
        from_attributes = True


class TicketResponse(BaseModel):
    id: str
    ticket_number: str
    feedback_id: str
    title: str
    description: str
    category: str
    priority: str
    status: str
    impact_summary: Optional[str]
    suggested_resolution: Optional[str]
    labels: Optional[List[str]]
    github_issue_number: Optional[int]
    github_issue_url: Optional[str]
    github_synced: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TicketUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    priority: Optional[str] = None
    status: Optional[str] = None
    impact_summary: Optional[str] = None
    suggested_resolution: Optional[str] = None


class ReviewDecision(BaseModel):
    action: str  # approve, reject, modify
    reviewer: str
    notes: Optional[str] = None
    modified_category: Optional[str] = None
    modified_priority: Optional[str] = None


class AgentRunResponse(BaseModel):
    id: str
    agent_name: str
    status: str
    latency_ms: Optional[float]
    tokens_used: Optional[int]
    estimated_cost: Optional[float]
    error_message: Optional[str]
    started_at: datetime
    completed_at: Optional[datetime]

    class Config:
        from_attributes = True


from typing import TypeVar, Generic
T = TypeVar('T')

class PaginatedResponse(BaseModel, Generic[T]):
    items: List[T]
    total: int


class AnalyticsOverview(BaseModel):
    total_feedback: int
    processed_today: int
    pending_review: int
    open_tickets: int
    avg_confidence: float
    category_distribution: Dict[str, int]
    priority_distribution: Dict[str, int]
    sentiment_distribution: Dict[str, int]
    source_distribution: Dict[str, int]
    processing_success_rate: float
    avg_agent_latency_ms: float
    total_tokens: int
    total_cost_usd: float


class TrendPoint(BaseModel):
    date: str
    count: int
    category: Optional[str] = None
    sentiment: Optional[str] = None


class MonitoringMetrics(BaseModel):
    agent_success_rate: Dict[str, float]
    agent_avg_latency: Dict[str, float]
    total_runs_24h: int
    failed_runs_24h: int
    throughput_per_hour: float
    last_ingestion: Optional[datetime]
    ingestion_sources: Dict[str, int]
    total_tokens_24h: int
    total_cost_24h_usd: float
