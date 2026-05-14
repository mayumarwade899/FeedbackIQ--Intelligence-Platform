"""
conftest.py — Shared fixtures for all agent tests.
"""
import os
import sys
from datetime import datetime

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


@pytest.fixture
def base_state() -> dict:
    """A valid AgentState dict pre-filled with safe test values."""
    return {
        "raw_feedback_id": "test-feedback-id-1234",
        "source": "google_play",
        "text": "This is a test feedback item.",
        "title": "Test Feedback",
        "metadata": {"app_id": "com.test.app", "rating": 3},
        "errors": [],
        "agent_traces": [],
        "processing_start": datetime.utcnow().isoformat(),
    }
