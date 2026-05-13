"""Agent pipeline status endpoints."""
from fastapi import APIRouter

router = APIRouter()

AGENT_LIST = [
    {"name": "ingestion_agent", "role": "Fetches feedback from GitHub, Reddit, Manual", "type": "ingestion"},
    {"name": "classification_agent", "role": "Classifies feedback into Bug/Feature/etc.", "type": "processing"},
    {"name": "sentiment_agent", "role": "Extracts sentiment and emotion tags", "type": "processing"},
    {"name": "duplicate_detection_agent", "role": "Vector-based deduplication", "type": "processing"},
    {"name": "insights_agent", "role": "Generates impact summary and resolution suggestions", "type": "processing"},
    {"name": "ticket_generation_agent", "role": "Builds structured actionable tickets", "type": "processing"},
    {"name": "orchestrator", "role": "Coordinates the full agent pipeline via LangGraph", "type": "orchestration"},
]


@router.get("")
async def list_agents():
    return {"agents": AGENT_LIST, "total": len(AGENT_LIST)}


@router.get("/pipeline")
async def pipeline_diagram():
    return {
        "nodes": [a["name"] for a in AGENT_LIST],
        "edges": [
            ["ingestion_agent", "orchestrator"],
            ["orchestrator", "classification_agent"],
            ["classification_agent", "sentiment_agent"],
            ["sentiment_agent", "duplicate_detection_agent"],
            ["duplicate_detection_agent", "insights_agent"],
            ["insights_agent", "ticket_generation_agent"],
        ],
        "conditional_edges": {
            "classification_agent": {
                "Spam": "END",
                "other": "sentiment_agent",
            },
            "duplicate_detection_agent": {
                "is_duplicate": "END",
                "unique": "insights_agent",
            },
        },
    }
