"""
Assistant skill – general Q&A fallback via LLMPort with short-term history and long-term memory (RAG).
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
    """Catch-all general Q&A via LLM with context history and long-term memory lookup."""

    def __init__(self) -> None:
        self._history: dict[str, list[dict[str, str]]] = {}

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

        memory = ctx.ports.get("memory")
        long_term_context = ""

        # 1. Long-Term Memory (RAG) Lookup
        if memory is not None:
            try:
                hits = await memory.search(ctx.raw_text, k=3)
                # Keep facts that have high relevance
                valid_facts = [
                    h["text"] for h in hits if h.get("similarity", 1.0) >= 0.5
                ]
                if valid_facts:
                    long_term_context = (
                        "\n\nRelevant context from past conversations/memories:\n"
                        + "\n".join(f"- {fact}" for fact in valid_facts)
                    )
            except Exception as e:
                logger.warning(
                    "Failed to search MemoryStore for assistant context: %s", e
                )

        # Build custom system prompt with RAG context
        system_prompt = _SYSTEM_PROMPT + long_term_context

        # 2. Short-Term History context formatting
        user_id = ctx.user_id or "unknown"
        history = self._history.setdefault(user_id, [])

        prompt_parts = []
        for turn in history:
            prompt_parts.append(f"{turn['role'].upper()}: {turn['content']}")
        prompt_parts.append(f"USER: {ctx.raw_text}")
        prompt_str = "\n".join(prompt_parts)

        try:
            response = await llm.generate(
                prompt_str,
                system=system_prompt,
            )

            # Save to conversation history
            history.append({"role": "user", "content": ctx.raw_text})
            history.append({"role": "assistant", "content": response})

            # Limit history to last 5 turns (10 messages total)
            if len(history) > 10:
                self._history[user_id] = history[-10:]

            return SkillResult(spoken_response=response, success=True)
        except Exception as exc:
            logger.error("Assistant LLM call failed: %s", exc)
            return SkillResult(
                spoken_response="I'm sorry, I couldn't process that right now.",
                success=False,
            )
