"""
Unified context assembler for local LLM prompts.

Constructs a structured, token-budgeted prompt with identity,
time awareness, RAG memories, conversation history, and active state.
"""

from __future__ import annotations

import logging
import time
from datetime import datetime
from typing import Any, Optional

from packages.core.expression.personality import get_personality_block

logger = logging.getLogger(__name__)

# ── Token budget constants ──
# Llama 3.2 3B with n_ctx=4096.  Reserve ~1000 tokens for the response.
_MAX_CONTEXT_TOKENS = 2800
_CHARS_PER_TOKEN = 3.5  # rough estimate for English/Devanagari mix

_RAG_MIN_SCORE = 0.5
_RAG_MAX_HITS = 3
_MAX_HISTORY_CHARS = 1800  # increased from 1200 with larger context window

# ── Language instructions ──
_LANG_INSTRUCTIONS = {
    "en": "Respond ONLY in English.",
    "hi": "Respond ONLY in Hindi (Devanagari script). Do NOT use English.",
    "mr": "Respond ONLY in Marathi (Devanagari script). Do NOT use English.",
}

_BASE_SYSTEM = (
    "You are FamilyRobot, a helpful family assistant for an 8-member Indian "
    "household. Keep answers concise, warm, and family-friendly."
)


class ContextBuilder:
    """Assembles a structured, token-budgeted system prompt and user prompt
    for the local LLM.

    Sections (injected in priority order):
      1. Identity & Time  (always included)
      2. Language instruction (always included)
      3. Active State (media, timers)
      4. Long-term RAG facts
      5. Conversation history (oldest trimmed first)
    """

    def __init__(
        self,
        *,
        max_context_chars: int = int(_MAX_CONTEXT_TOKENS * _CHARS_PER_TOKEN),
        rag_min_score: float = _RAG_MIN_SCORE,
        rag_max_hits: int = _RAG_MAX_HITS,
        max_history_chars: int = _MAX_HISTORY_CHARS,
    ) -> None:
        self._max_chars = max_context_chars
        self._rag_min_score = rag_min_score
        self._rag_max_hits = rag_max_hits
        self._max_history_chars = max_history_chars

    async def build_system_prompt(
        self,
        *,
        user_name: str = "Someone",
        user_role: str = "unknown",
        language: str = "en",
        memory_port: Any = None,
        query: str = "",
        is_guest: bool = False,
        active_state: Optional[dict] = None,
    ) -> str:
        """Return a fully assembled system prompt string."""
        sections: list[str] = [_BASE_SYSTEM]
        budget = self._max_chars

        # 1. Language instruction (always)
        lang_inst = _LANG_INSTRUCTIONS.get(language, _LANG_INSTRUCTIONS["en"])
        sections.append(lang_inst)

        # 2. Identity & Time awareness
        now = datetime.now()
        time_str = now.strftime("%I:%M %p")
        day_str = now.strftime("%A, %B %d")
        greeting_period = _get_greeting_period(now.hour)

        identity_block = (
            f"\nCurrent context: It is {greeting_period}, {time_str} on {day_str}. "
            f"You are speaking with {user_name} (role: {user_role})."
        )
        sections.append(identity_block)

        # 2b. Personality profile (role-appropriate tone and cultural awareness)
        personality_block = get_personality_block(
            user_role=user_role,
            user_name=user_name,
        )
        if personality_block:
            sections.append(personality_block)

        # 3. Active State (media, timers — if available)
        if active_state:
            state_parts = []
            if active_state.get("is_playing_music"):
                song = active_state.get("current_song", "unknown")
                state_parts.append(f"Currently playing music: \"{song}\".")
            if state_parts:
                sections.append("\nActive state: " + " ".join(state_parts))

        # 4. RAG memories (skip for guests)
        if not is_guest and memory_port and query:
            rag_block = await self._rag_lookup(memory_port, query)
            if rag_block:
                sections.append(rag_block)

        # Assemble and check budget
        system = " ".join(sections[:2]) + "".join(sections[2:])
        if len(system) > budget:
            system = system[:budget]

        return system

    def build_history_prompt(
        self,
        history: list,
        current_text: str,
    ) -> str:
        """Format conversation history + current query, respecting char budget."""
        parts: list[str] = []
        budget = self._max_history_chars

        # Walk from newest to oldest, collecting what fits
        selected: list[str] = []
        for turn in reversed(history):
            role = turn.role if hasattr(turn, "role") else turn.get("role", "user")
            content = turn.content if hasattr(turn, "content") else turn.get("content", "")
            line = f"{role.upper()}: {content}"
            if budget - len(line) < 0:
                break
            selected.append(line)
            budget -= len(line)

        # Reverse back to chronological order
        parts.extend(reversed(selected))
        parts.append(f"USER: {current_text}")
        return "\n".join(parts)

    async def _rag_lookup(self, memory_port: Any, query: str) -> str:
        """Query MemoryStore and return formatted context string."""
        try:
            hits = await memory_port.search(query, k=self._rag_max_hits)
            valid_facts = [
                h["text"] for h in hits if h.get("score", 0.0) >= self._rag_min_score
            ]
            if valid_facts:
                # Boost recently stored facts with a label
                facts_block = "\n".join(f"- {f}" for f in valid_facts)
                return (
                    "\n\nRelevant context from past "
                    "conversations/memories:\n" + facts_block
                )
        except Exception as exc:
            logger.warning("MemoryStore search failed during context build: %s", exc)
        return ""


def _get_greeting_period(hour: int) -> str:
    """Return a time-of-day greeting phrase."""
    if hour < 5:
        return "late night"
    elif hour < 12:
        return "morning"
    elif hour < 17:
        return "afternoon"
    elif hour < 21:
        return "evening"
    else:
        return "night"
