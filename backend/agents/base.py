"""
Base Agent — Abstract foundation for all specialized agents.
Includes monitoring, retry logic, LangSmith tracing, and error handling.
"""
from __future__ import annotations

import asyncio
import logging
import time
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, Optional

from core.config import settings
from core.schemas import AgentState

logger = logging.getLogger(__name__)


class AgentExecutionError(Exception):
    pass


class BaseAgent(ABC):
    """
    Abstract base class for all agents in the pipeline.
    Provides: retry logic, latency tracking, error capture, LangSmith integration.
    """

    name: str = "base_agent"
    version: str = "2.0.0"
    max_retries: int = 3
    retry_delay: float = 1.0

    def __init__(self):
        self.logger = logging.getLogger(f"agents.{self.name}")

    async def execute(self, state: AgentState) -> AgentState:
        """
        Public execution interface with full observability wrapping.
        """
        start = time.monotonic()
        trace: Dict[str, Any] = {
            "agent": self.name,
            "version": self.version,
            "started_at": datetime.utcnow().isoformat(),
            "status": "running",
        }

        for attempt in range(1, self.max_retries + 1):
            try:
                self.logger.info(
                    "Agent=%s attempt=%d feedback=%s",
                    self.name, attempt,
                    state.get("raw_feedback_id", "unknown"),
                )
                updated_state = await self._run(state)
                latency_ms = (time.monotonic() - start) * 1000

                # Capture usage from state if agent provided it
                usage = updated_state.pop("_last_usage", None) if isinstance(updated_state, dict) else None

                trace.update({
                    "status": "success",
                    "latency_ms": round(latency_ms, 2),
                    "attempt": attempt,
                    "prompt_tokens": usage.get("prompt_tokens") if usage else 0,
                    "completion_tokens": usage.get("candidates_tokens") if usage else 0,
                    "total_tokens": usage.get("total_tokens") if usage else 0,
                })
                self.logger.info(
                    "Agent=%s completed latency=%.1fms tokens=%s", 
                    self.name, latency_ms, usage.get("total_tokens") if usage else 0
                )

                # Append trace to state
                traces = updated_state.get("agent_traces", [])
                traces.append(trace)
                updated_state["agent_traces"] = traces

                return updated_state

            except Exception as exc:
                self.logger.warning(
                    "Agent=%s attempt=%d failed: %s", self.name, attempt, exc
                )
                if attempt < self.max_retries:
                    await asyncio.sleep(self.retry_delay * attempt)
                else:
                    latency_ms = (time.monotonic() - start) * 1000
                    trace.update({
                        "status": "failed",
                        "error": str(exc),
                        "latency_ms": round(latency_ms, 2),
                        "attempt": attempt,
                    })
                    errors = state.get("errors", [])
                    errors.append(f"{self.name}: {exc}")
                    state["errors"] = errors
                    traces = state.get("agent_traces", [])
                    traces.append(trace)
                    state["agent_traces"] = traces
                    
                    # Apply heuristic fallback if available so pipeline doesn't break
                    state = self._fallback(state)
                    
                    # Return state with error noted — don't crash the pipeline
                    return state

        return state

    @abstractmethod
    async def _run(self, state: AgentState) -> AgentState:
        """Agent-specific implementation."""
        raise NotImplementedError

    def _fallback(self, state: AgentState) -> AgentState:
        """Optional fallback logic when all LLM retries fail."""
        return state
