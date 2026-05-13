"""
Application Configuration — Environment-driven settings management.
"""
from __future__ import annotations

import os
from typing import List, Optional
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    # Application
    APP_NAME: str = "Feedback Intelligence Platform"
    APP_VERSION: str = "2.0.0"
    DEBUG: bool = False
    SECRET_KEY: str = Field(default="change-me-in-production", env="SECRET_KEY")

    # Database
    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/feedback_platform",
        env="DATABASE_URL",
    )
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20

    # Redis (for caching & task queue)
    REDIS_URL: str = Field(default="redis://localhost:6379/0", env="REDIS_URL")

    # LLM — Gemini
    GOOGLE_API_KEY: Optional[str] = Field(default=None, env="GOOGLE_API_KEY")
    GEMINI_MODEL: str = Field(default="gemini-2.0-flash", env="GEMINI_MODEL")
    GEMINI_TEMPERATURE: float = 0.1
    GEMINI_MAX_TOKENS: int = 2048

    # Gemini Pricing (per 1M tokens)
    GEMINI_COST_INPUT_1M: float = 0.075
    GEMINI_COST_OUTPUT_1M: float = 0.30

    # LangSmith Observability
    LANGCHAIN_API_KEY: Optional[str] = Field(default=None, env="LANGCHAIN_API_KEY")
    LANGCHAIN_PROJECT: str = Field(default="feedback-intelligence", env="LANGCHAIN_PROJECT")
    LANGCHAIN_TRACING_V2: bool = Field(default=False, env="LANGCHAIN_TRACING_V2")
    LANGCHAIN_ENDPOINT: str = "https://api.smith.langchain.com"

    # GitHub Integration
    GITHUB_TOKEN: Optional[str] = Field(default=None, env="GITHUB_TOKEN")
    GITHUB_REPO_OWNER: Optional[str] = Field(default=None, env="GITHUB_REPO_OWNER")
    GITHUB_REPO_NAME: Optional[str] = Field(default=None, env="GITHUB_REPO_NAME")
    GITHUB_ISSUES_ENABLED: bool = False

    # Google Play Store
    GOOGLE_PLAY_APP_ID: Optional[str] = Field(default=None, env="GOOGLE_PLAY_APP_ID")
    GOOGLE_PLAY_REVIEW_COUNT: int = Field(default=100, env="GOOGLE_PLAY_REVIEW_COUNT")

    # Reddit Integration
    REDDIT_CLIENT_ID: Optional[str] = Field(default=None, env="REDDIT_CLIENT_ID")
    REDDIT_CLIENT_SECRET: Optional[str] = Field(default=None, env="REDDIT_CLIENT_SECRET")
    REDDIT_USER_AGENT: str = "FeedbackIntelligencePlatform/2.0"
    REDDIT_SUBREDDITS: List[str] = ["MachineLearning", "artificial"]

    # Ingestion Scheduler
    INGESTION_INTERVAL_MINUTES: int = Field(default=15, env="INGESTION_INTERVAL_MINUTES")
    INGESTION_ENABLED: bool = Field(default=True, env="INGESTION_ENABLED")
    MAX_INGESTION_BATCH: int = 20

    # Agent Configuration
    SIMILARITY_THRESHOLD: float = 0.65
    CONFIDENCE_THRESHOLD: float = 0.6
    MAX_AGENT_RETRIES: int = 3
    AGENT_TIMEOUT_SECONDS: int = 30

    # Moderation Thresholds
    # Reviews with toxicity_score >= EXTREME are silently skipped (no insights/ticket).
    # Reviews with toxicity_score >= SOFT (but below EXTREME) are masked and still processed.
    TOXICITY_SOFT_THRESHOLD: float = Field(default=0.5, env="TOXICITY_SOFT_THRESHOLD")
    TOXICITY_EXTREME_THRESHOLD: float = Field(default=0.85, env="TOXICITY_EXTREME_THRESHOLD")

    # CORS
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
    ]

    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()


def configure_langsmith():
    """Set LangSmith environment variables for tracing."""
    if settings.LANGCHAIN_API_KEY:
        os.environ["LANGCHAIN_API_KEY"] = settings.LANGCHAIN_API_KEY
        os.environ["LANGCHAIN_PROJECT"] = settings.LANGCHAIN_PROJECT
        os.environ["LANGCHAIN_TRACING_V2"] = str(settings.LANGCHAIN_TRACING_V2).lower()
        os.environ["LANGCHAIN_ENDPOINT"] = settings.LANGCHAIN_ENDPOINT
