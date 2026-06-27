"""
Assistant skill – general Q&A fallback via LLMPort.

Supports:
- **Short-term conversation history**: sliding window of recent turns
  per user with timestamps, session-timeout eviction, and LRU user cap.
- **Long-term memory (RAG)**: queries the vector MemoryStore for relevant
  past facts and injects them into the LLM system prompt.
"""

from __future__ import annotations

import logging
import time
from collections import OrderedDict

from packages.core.skills.base import BaseSkill, SkillContext, SkillResult

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = (
    "You are FamilyRobot, a helpful family assistant for an 8-member Indian "
    "household. Keep answers concise, warm, and family-friendly."
)

# Explicit language constraints the local LLM (3B params) actually follows
_LANG_INSTRUCTIONS = {
    "hi": " Respond ONLY in Hindi (Devanagari script). Do NOT use English.",
    "mr": " Respond ONLY in Marathi (Devanagari script). Do NOT use English.",
}

# ── Tuning constants ──
_MAX_HISTORY_TURNS: int = 5  # turns (user+assistant pairs) retained
_MAX_HISTORY_CHARS: int = 1200  # char budget for history block (~400 tokens)
_MAX_USERS: int = 16  # LRU cap on concurrent user histories
_SESSION_TIMEOUT_S: float = 300.0  # 5 min silence → reset conversation
_RAG_MIN_SCORE: float = 0.5  # minimum cosine similarity for RAG hits
_RAG_MAX_HITS: int = 3  # max memories to retrieve


class _ConversationTurn:
    """Single user↔assistant exchange with a timestamp."""

    __slots__ = ("role", "content", "timestamp")

    def __init__(self, role: str, content: str) -> None:
        self.role = role
        self.content = content
        self.timestamp = time.monotonic()


class AssistantSkill(BaseSkill):
    """Catch-all general Q&A via LLM with context-aware memory."""

    def __init__(
        self,
        *,
        max_users: int = _MAX_USERS,
        session_timeout_s: float = _SESSION_TIMEOUT_S,
        max_history_chars: int = _MAX_HISTORY_CHARS,
    ) -> None:
        # OrderedDict gives O(1) LRU eviction via move_to_end/popitem
        self._history: OrderedDict[str, list[_ConversationTurn]] = OrderedDict()
        self._max_users = max_users
        self._session_timeout_s = session_timeout_s
        self._max_history_chars = max_history_chars

    @property
    def name(self) -> str:
        return "assistant"

    @property
    def required_permissions(self) -> list[str]:
        return ["general_info"]

    # ── main entry point ──

    async def execute(self, ctx: SkillContext) -> SkillResult:
        llm = ctx.ports.get("llm")
        if llm is None:
            return SkillResult(
                spoken_response=("I'm sorry, I can't answer questions right now."),
                success=False,
            )

        # 1. Long-Term Memory (RAG) Lookup
        #    SEC: guests must NOT receive RAG injection (AGENTS.md rule)
        long_term_context = ""
        is_guest = (ctx.user_role or "").lower() == "guest"
        if not is_guest:
            long_term_context = await self._rag_lookup(ctx)

        # Build explicit language instruction from detected spoken language
        lang_code = getattr(ctx, "language", "en") or "en"
        lang_instruction = _LANG_INSTRUCTIONS.get(
            lang_code, " Respond ONLY in English."
        )
        system_prompt = _SYSTEM_PROMPT + lang_instruction + long_term_context

        # 2. Short-Term Conversation History
        user_id = ctx.user_id or "unknown"
        history = self._get_or_create_history(user_id)

        # Session timeout: clear stale context
        if history and self._is_session_expired(history):
            history.clear()

        prompt_str = self._build_prompt(history, ctx.raw_text)

        try:
            response = await llm.generate(
                prompt_str,
                system=system_prompt,
            )

            # Persist this exchange
            history.append(_ConversationTurn("user", ctx.raw_text))
            history.append(_ConversationTurn("assistant", response))

            # Trim to max turns (each turn = 2 entries)
            max_entries = _MAX_HISTORY_TURNS * 2
            if len(history) > max_entries:
                del history[: len(history) - max_entries]

            return SkillResult(spoken_response=response, success=True)
        except Exception as exc:
            logger.error("Assistant LLM call failed: %s", exc)
            return SkillResult(
                spoken_response=("I'm sorry, I couldn't process that right now."),
                success=False,
            )

    # ── RAG helpers ──

    async def _rag_lookup(self, ctx: SkillContext) -> str:
        """Query MemoryStore and return formatted context string."""
        memory = ctx.ports.get("memory")
        if memory is None:
            return ""
        try:
            hits = await memory.search(ctx.raw_text, k=_RAG_MAX_HITS)
            # BUG-A1 fix: MemoryStore returns "score", not "similarity"
            valid_facts = [
                h["text"] for h in hits if h.get("score", 0.0) >= _RAG_MIN_SCORE
            ]
            if valid_facts:
                facts_block = "\n".join(f"- {f}" for f in valid_facts)
                return (
                    "\n\nRelevant context from past "
                    "conversations/memories:\n" + facts_block
                )
        except Exception as exc:
            logger.warning("MemoryStore search failed: %s", exc)
        return ""

    # ── History helpers ──

    def _get_or_create_history(self, user_id: str) -> list[_ConversationTurn]:
        """Return (or create) the history list for *user_id* with LRU eviction."""
        if user_id in self._history:
            self._history.move_to_end(user_id)
            return self._history[user_id]

        # Evict oldest user if at capacity
        while len(self._history) >= self._max_users:
            evicted_id, _ = self._history.popitem(last=False)
            logger.debug("Evicted stale history for user %s", evicted_id)

        self._history[user_id] = []
        return self._history[user_id]

    def _is_session_expired(self, history: list[_ConversationTurn]) -> bool:
        """True if the last turn is older than the session timeout."""
        if not history:
            return False
        elapsed = time.monotonic() - history[-1].timestamp
        return elapsed > self._session_timeout_s

    def _build_prompt(
        self,
        history: list[_ConversationTurn],
        current_text: str,
    ) -> str:
        """Format history + current query, respecting the char budget."""
        parts: list[str] = []
        budget = self._max_history_chars

        # Walk from newest to oldest, collecting what fits
        selected: list[str] = []
        for turn in reversed(history):
            line = f"{turn.role.upper()}: {turn.content}"
            if budget - len(line) < 0:
                break
            selected.append(line)
            budget -= len(line)

        # Reverse back to chronological order
        parts.extend(reversed(selected))
        parts.append(f"USER: {current_text}")
        return "\n".join(parts)
