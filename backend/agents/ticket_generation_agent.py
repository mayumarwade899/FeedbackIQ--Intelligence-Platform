"""
Ticket Generation Agent — Builds structured, actionable tickets from enriched feedback.
"""
from __future__ import annotations

import hashlib
from datetime import datetime

from agents.base import BaseAgent
from agents.llm_client import get_llm
from core.schemas import AgentState

SYSTEM_PROMPT = """You are a professional technical writer creating issue tickets.
Given the feedback analysis, generate ONLY this JSON:
{
  "title": "<concise, specific ticket title — max 80 chars>",
  "description": "<markdown-formatted description with sections: ## Summary, ## Steps to Reproduce (if bug), ## Expected Behavior, ## Actual Behavior, ## Impact>",
  "labels": ["<label1>", "<label2>"]
}

Title guidelines:
- Be specific: "App crashes on PDF export — Android 14" not "App crash"
- Include platform/version if available
- Start with action verb for bugs: "Fix...", "Implement...", "Investigate..."

Label guidelines (pick relevant):
- Type: bug, feature-request, complaint, praise
- Priority: critical, high, medium, low
- Platform: android, ios, web, mac, windows
- Component: auth, sync, export, ui, performance, api"""


class TicketGenerationAgent(BaseAgent):
    name = "ticket_generation_agent"

    async def _run(self, state: AgentState) -> AgentState:
        text = state.get("text", "")
        title = state.get("title", "")
        category = state.get("category", "")
        priority = state.get("priority", "Medium")
        impact = state.get("impact_summary", "")
        resolution = state.get("suggested_resolution", "")
        technical = state.get("technical_details", {})
        sentiment = state.get("sentiment", "neutral")

        context = f"""
            Category: {category}
            Priority: {priority}
            Sentiment: {sentiment}
            Original Title: {title}
            Feedback: {text}
            Impact Summary: {impact}
            Suggested Resolution: {resolution}
            Technical Details: {technical}
        """
        llm = get_llm()

        usage = None
        if llm.available:
            result_obj = await llm.generate_json(
                SYSTEM_PROMPT,
                f"Generate ticket:\n{context[:3000]}"
            )
            result = result_obj["data"]
            usage = result_obj["usage"]
        else:
            result = self._generate_heuristic(text, title, category, priority)

        state["_last_usage"] = usage
        state["ticket_title"] = result.get("title", title or f"{category} feedback")[:200]
        state["ticket_description"] = result.get("description", text)
        state["ticket_labels"] = result.get("labels", [category.lower(), priority.lower()])

        return state

    def _fallback(self, state: AgentState) -> AgentState:
        """Called by BaseAgent if all LLM retries fail."""
        text = state.get("text", "")
        title = state.get("title", "")
        category = state.get("category", "Complaint")
        priority = state.get("priority", "Medium")
        
        result = self._generate_heuristic(text, title, category, priority)
        
        state["ticket_title"] = result.get("title")[:200]
        state["ticket_description"] = result.get("description")
        state["ticket_labels"] = result.get("labels")
        
        return state

    def _generate_heuristic(self, text: str, title: str, category: str, priority: str) -> dict:
        ticket_title = title or text[:80].strip() or "Feedback Report"
        description = f"""## Summary\n{text}\n\n## Category\n{category}\n\n## Priority\n{priority}\n\n## Impact\nReview required — automated ticket generated from user feedback."""
        labels = [category.lower().replace(" ", "-"), priority.lower()]
        return {
            "title": ticket_title,
            "description": description,
            "labels": labels,
        }
