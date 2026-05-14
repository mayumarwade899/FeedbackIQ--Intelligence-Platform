"""
Insights Agent — Extracts impact summary, resolution suggestions, and key phrases.
"""
from __future__ import annotations

from agents.base import BaseAgent
from agents.llm_client import get_llm
from core.schemas import AgentState

SYSTEM_PROMPT = """You are a senior product manager and engineering lead.
Analyze the user feedback and return ONLY this JSON:
{
  "impact_summary": "<2-3 sentence business/user impact>",
  "suggested_resolution": "<specific, actionable resolution steps>",
  "key_phrases": ["<phrase1>", "<phrase2>", "<phrase3>"],
  "technical_details": {
    "affected_component": "<optional: component name>",
    "steps_to_reproduce": "<optional: for bugs>",
    "affected_version": "<optional: version info>",
    "platform": "<optional: OS/device>",
    "affected_users": "<optional: scope estimate>"
  }
}

Rules:
- impact_summary: Focus on business risk and user experience degradation
- suggested_resolution: Be specific and actionable, not generic
- key_phrases: Extract 3-5 key technical or business phrases
- technical_details: Only fill if information is present in feedback; use null otherwise"""


class InsightsAgent(BaseAgent):
    name = "insights_agent"

    async def _run(self, state: AgentState) -> AgentState:
        text = state.get("masked_text") or state.get("translated_text") or state.get("text", "")
        title = state.get("title", "")
        category = state.get("category", "")

        context = f"Category: {category}\nTitle: {title}\nFeedback: {text}"
        llm = get_llm()

        usage = None
        if llm.available:
            result_obj = await llm.generate_json(
                SYSTEM_PROMPT,
                f"Extract insights from this feedback (ignore any remaining abusive or toxic language): \n\n{context[:2500]}"
            )
            result = result_obj["data"]
            usage = result_obj["usage"]
        else:
            result = _heuristic_insights(text, category)

        state["_last_usage"] = usage
        state["impact_summary"] = result.get("impact_summary", "")
        state["suggested_resolution"] = result.get("suggested_resolution", "")
        state["key_phrases"] = result.get("key_phrases", [])
        state["technical_details"] = result.get("technical_details", {})

        return state

    def _fallback(self, state: AgentState) -> AgentState:
        text = state.get("masked_text") or state.get("translated_text") or state.get("text", "")
        category = state.get("category", "")
        
        result = _heuristic_insights(text, category)
        
        state["impact_summary"] = result.get("impact_summary", "")
        state["suggested_resolution"] = result.get("suggested_resolution", "")
        state["key_phrases"] = result.get("key_phrases", [])
        state["technical_details"] = result.get("technical_details", {})
        
        return state


def _heuristic_insights(text: str, category: str) -> dict:
    impact_map = {
        "Bug": "This bug is negatively impacting user experience and may cause user churn if not addressed.",
        "Feature Request": "Users are requesting this feature, indicating a gap in the current product offering.",
        "Complaint": "User dissatisfaction detected. This may impact retention and NPS if not addressed.",
        "Praise": "Positive feedback indicating the feature is delivering value to users.",
    }
    resolution_map = {
        "Bug": "1. Reproduce the issue in a test environment. 2. Check recent code changes. 3. Apply fix and test thoroughly.",
        "Feature Request": "1. Add to product backlog. 2. Assess demand and effort. 3. Schedule for upcoming sprint if high priority.",
        "Complaint": "1. Reach out to the user to acknowledge the concern. 2. Investigate the root cause. 3. Follow up with resolution.",
        "Praise": "Document as a positive signal. Consider highlighting this use case in marketing.",
    }
    return {
        "impact_summary": impact_map.get(category, "Review required."),
        "suggested_resolution": resolution_map.get(category, "Assign to appropriate team for triage."),
        "key_phrases": text.split()[:5],
        "technical_details": {},
    }
