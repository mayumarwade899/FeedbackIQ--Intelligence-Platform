"""
Feedback Intelligence Platform — FastAPI Application Entry Point
Production-grade multi-agent feedback processing system.
"""
from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

from api.routes import feedback, tickets, analytics, agents, monitoring, ingestion
from core.config import settings
from core.logging_config import configure_logging
from db.database import engine, Base
from workers.scheduler import start_scheduler, stop_scheduler

configure_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown lifecycle."""
    logger.info("🚀 Starting Feedback Intelligence Platform v2.0")

    # Create all DB tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("✅ Database tables initialized")

    # Start background scheduler
    await start_scheduler()
    logger.info("✅ Background scheduler started")

    yield

    # Shutdown
    await stop_scheduler()
    logger.info("🛑 Feedback Intelligence Platform shut down")


app = FastAPI(
    title="Feedback Intelligence Platform",
    description="Production-grade Multi-Agent AI Feedback Processing System",
    version="2.0.0",
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

# Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(GZipMiddleware, minimum_size=1000)

# Routers
app.include_router(feedback.router, prefix="/api/feedback", tags=["Feedback"])
app.include_router(tickets.router, prefix="/api/tickets", tags=["Tickets"])
app.include_router(analytics.router, prefix="/api/analytics", tags=["Analytics"])
app.include_router(agents.router, prefix="/api/agents", tags=["Agents"])
app.include_router(monitoring.router, prefix="/api/monitoring", tags=["Monitoring"])
app.include_router(ingestion.router, prefix="/api/ingestion", tags=["Ingestion"])


@app.get("/api/health")
async def health_check():
    return {
        "status": "healthy",
        "version": "2.0.0",
        "platform": "Feedback Intelligence Platform",
    }
