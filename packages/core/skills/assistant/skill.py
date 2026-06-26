"""
Assistant skill – general Q&A fallback via LLMPort.

Handles any utterance that doesn't match a specific skill.
"""

from __future__ import annotations

import logging

from packages.core.skills.base import BaseSkill, SkillContext, SkillResult

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = (
    "You are FamilyRobot, a helpful family assistant for an 8-member Indian "
    "household. Keep answers concise, warm, and family-friendly. "
    "Answer in the language the user spoke."
)


class AssistantSkill(BaseSkill):
    """Catch-all general Q&A via LLM."""

    @property
    def name(self) -> str:
        return "assistant"

    @property
    def required_permissions(self) -> list[str]:
        return ["general_info"]

    async def execute(self, ctx: SkillContext) -> SkillResult:
        llm = ctx.ports.get("llm")
        if llm is None:
            return SkillResult(
                spoken_response="I'm sorry, I can't answer questions right now.",
                success=False,
            )

        try:
            response = await llm.generate(
                ctx.raw_text,
                system=_SYSTEM_PROMPT,
            )
            return SkillResult(spoken_response=response)
        except Exception as exc:
            logger.error("Assistant LLM call failed: %s", exc)
            return SkillResult(
                spoken_response="I'm sorry, I couldn't process that right now.",
                success=False,
            )
