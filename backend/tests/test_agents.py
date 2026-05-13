"""
test_agents.py — 10 pytest tests for the AI agent pipeline.
No real Gemini API calls are made; all LLM interactions are mocked.
"""
from __future__ import annotations

import os
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Ensure backend/ is on the path (also set in conftest, but explicit here for safety)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


# ─────────────────────────────────────────────────────────────────────────────
# 1. Classification: Bug
# ─────────────────────────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_classification_agent_bug(base_state):
    """Heuristic mode classifies 'app crashes on login' as Bug with High/Critical priority."""
    from agents.classification_agent import ClassificationAgent

    base_state["text"] = "app crashes on login"
    base_state["translated_text"] = None

    mock_llm = MagicMock()
    mock_llm.available = False

    with patch("agents.classification_agent.get_llm", return_value=mock_llm):
        agent = ClassificationAgent()
        state = await agent.execute(base_state)

    assert state["category"] == "Bug"
    assert state["priority"] in ("High", "Critical")


# ─────────────────────────────────────────────────────────────────────────────
# 2. Classification: Spam
# ─────────────────────────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_classification_agent_spam(base_state):
    """Heuristic mode classifies spam text correctly."""
    from agents.classification_agent import ClassificationAgent

    base_state["text"] = "BUY FOLLOWERS FAST visit spamlink.com"
    base_state["translated_text"] = None

    mock_llm = MagicMock()
    mock_llm.available = False

    with patch("agents.classification_agent.get_llm", return_value=mock_llm):
        agent = ClassificationAgent()
        state = await agent.execute(base_state)

    assert state["category"] == "Spam"


# ─────────────────────────────────────────────────────────────────────────────
# 3. Classification: Feature Request
# ─────────────────────────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_classification_agent_feature_request(base_state):
    """Heuristic mode classifies feature-request phrasing correctly."""
    from agents.classification_agent import ClassificationAgent

    base_state["text"] = "would love to see dark mode added"
    base_state["translated_text"] = None

    mock_llm = MagicMock()
    mock_llm.available = False

    with patch("agents.classification_agent.get_llm", return_value=mock_llm):
        agent = ClassificationAgent()
        state = await agent.execute(base_state)

    assert state["category"] == "Feature Request"


# ─────────────────────────────────────────────────────────────────────────────
# 4. Sentiment: Negative
# ─────────────────────────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_sentiment_agent_negative(base_state):
    """Heuristic mode detects negative sentiment and a negative score."""
    from agents.sentiment_agent import SentimentAgent

    base_state["text"] = "this app is terrible and keeps crashing"
    base_state["translated_text"] = None

    mock_llm = MagicMock()
    mock_llm.available = False

    with patch("agents.sentiment_agent.get_llm", return_value=mock_llm):
        agent = SentimentAgent()
        state = await agent.execute(base_state)

    assert state["sentiment"] == "negative"
    assert state["sentiment_score"] < 0


# ─────────────────────────────────────────────────────────────────────────────
# 5. Sentiment: Positive
# ─────────────────────────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_sentiment_agent_positive(base_state):
    """Heuristic mode detects positive sentiment and a positive score."""
    from agents.sentiment_agent import SentimentAgent

    base_state["text"] = "amazing app love everything about it"
    base_state["translated_text"] = None

    mock_llm = MagicMock()
    mock_llm.available = False

    with patch("agents.sentiment_agent.get_llm", return_value=mock_llm):
        agent = SentimentAgent()
        state = await agent.execute(base_state)

    assert state["sentiment"] == "positive"
    assert state["sentiment_score"] > 0


# ─────────────────────────────────────────────────────────────────────────────
# 6. Duplicate Detection: No Duplicates
# ─────────────────────────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_duplicate_detection_no_duplicates(base_state):
    """When the DB returns no results, feedback is not flagged as duplicate.
    Embedding should be a list of 128 floats (dim=128 from _tfidf_embedding)."""
    from agents.duplicate_detection_agent import DuplicateDetectionAgent

    base_state["text"] = "this is a completely unique piece of feedback"
    base_state["translated_text"] = None

    agent = DuplicateDetectionAgent()

    with patch.object(agent, "_find_similar", new=AsyncMock(return_value=(None, 0.0))):
        state = await agent.execute(base_state)

    assert state["is_duplicate"] is False
    assert isinstance(state["embedding"], list)
    assert len(state["embedding"]) == 128


# ─────────────────────────────────────────────────────────────────────────────
# 7. Duplicate Detection: Finds Duplicate
# ─────────────────────────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_duplicate_detection_finds_duplicate(base_state):
    """When DB returns a similar embedding above the threshold, is_duplicate is True."""
    from agents.duplicate_detection_agent import DuplicateDetectionAgent

    base_state["text"] = "app crashes every time I open it"
    base_state["translated_text"] = None

    agent = DuplicateDetectionAgent()

    with patch.object(agent, "_find_similar", new=AsyncMock(return_value=("existing-id-9999", 0.92))), \
         patch("agents.duplicate_detection_agent.settings") as mock_settings:
        mock_settings.SIMILARITY_THRESHOLD = 0.85
        state = await agent.execute(base_state)

    assert state["is_duplicate"] is True
    assert state["duplicate_of_id"] is not None


# ─────────────────────────────────────────────────────────────────────────────
# 8. Insights Agent: Heuristic Fallback
# ─────────────────────────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_insights_agent_heuristic_fallback(base_state):
    """With LLM unavailable, heuristic fallback produces non-empty impact_summary
    and suggested_resolution for a Bug category."""
    from agents.insights_agent import InsightsAgent

    base_state["text"] = "the export button does not work at all"
    base_state["translated_text"] = None
    base_state["category"] = "Bug"

    mock_llm = MagicMock()
    mock_llm.available = False

    with patch("agents.insights_agent.get_llm", return_value=mock_llm):
        agent = InsightsAgent()
        state = await agent.execute(base_state)

    assert isinstance(state["impact_summary"], str)
    assert len(state["impact_summary"]) > 0
    assert isinstance(state["suggested_resolution"], str)
    assert len(state["suggested_resolution"]) > 0


# ─────────────────────────────────────────────────────────────────────────────
# 9. Ticket Generation: Produces Valid Title and Labels
# ─────────────────────────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_ticket_generation_agent_produces_title(base_state):
    """With LLM unavailable, heuristic produces a valid ticket title (≤ 200 chars)
    and at least one label."""
    from agents.ticket_generation_agent import TicketGenerationAgent

    base_state["text"] = "The sync feature is completely broken after the last update"
    base_state["title"] = "Sync Broken"
    base_state["category"] = "Bug"
    base_state["priority"] = "High"
    base_state["sentiment"] = "negative"
    base_state["impact_summary"] = "Users cannot sync data."
    base_state["suggested_resolution"] = "Roll back the sync module."
    base_state["technical_details"] = {}

    mock_llm = MagicMock()
    mock_llm.available = False

    with patch("agents.ticket_generation_agent.get_llm", return_value=mock_llm):
        agent = TicketGenerationAgent()
        state = await agent.execute(base_state)

    assert isinstance(state["ticket_title"], str)
    assert len(state["ticket_title"]) > 0
    assert len(state["ticket_title"]) <= 200
    assert isinstance(state["ticket_labels"], list)
    assert len(state["ticket_labels"]) > 0


# ─────────────────────────────────────────────────────────────────────────────
# 10. Base Agent: Retry on Failure
# ─────────────────────────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_base_agent_retry_on_failure(base_state):
    """A concrete agent that fails on attempts 1 and 2 succeeds on attempt 3.
    The final agent_traces must contain exactly one 'success' trace with attempt == 3."""
    from agents.base import BaseAgent
    from core.schemas import AgentState

    call_count = 0

    class FlakyAgent(BaseAgent):
        name = "flaky_test_agent"
        max_retries = 3
        retry_delay = 0.0  # skip sleeps during tests

        async def _run(self, state: AgentState) -> AgentState:
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise RuntimeError(f"Simulated failure on attempt {call_count}")
            state["flaky_result"] = "success"
            return state

    agent = FlakyAgent()
    state = await agent.execute(dict(base_state))

    assert state.get("flaky_result") == "success"

    success_traces = [t for t in state.get("agent_traces", []) if t["status"] == "success"]
    assert len(success_traces) == 1
    assert success_traces[0]["attempt"] == 3
