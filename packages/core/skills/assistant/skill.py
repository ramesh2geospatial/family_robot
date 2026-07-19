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

from packages.core.cognition.context_builder import ContextBuilder
from packages.core.cognition.tool_executor import ToolExecutor
from packages.core.cognition.tool_registry import ToolRegistry
from packages.core.skills.base import BaseSkill, SkillContext, SkillResult

logger = logging.getLogger(__name__)

# ── Tuning constants ──
_MAX_HISTORY_TURNS: int = 5  # turns (user+assistant pairs) retained
_MAX_HISTORY_CHARS: int = 1800  # char budget for history block (increased for 4096 ctx)
_MAX_USERS: int = 16  # LRU cap on concurrent user histories
_SESSION_TIMEOUT_S: float = 300.0  # 5 min silence → reset conversation


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
        self._context_builder = ContextBuilder(
            max_history_chars=max_history_chars,
        )

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

        # 1. Build unified system prompt (identity, time, RAG, language)
        is_guest = (ctx.user_role or "").lower() == "guest"
        memory_port = ctx.ports.get("memory")

        # Gather active state from ports if available
        active_state = ctx.ports.get("active_state") or {}

        system_prompt = await self._context_builder.build_system_prompt(
            user_name=ctx.user_name or "Someone",
            user_role=ctx.user_role or "unknown",
            language=getattr(ctx, "language", "en") or "en",
            memory_port=memory_port if not is_guest else None,
            query=ctx.raw_text,
            is_guest=is_guest,
            active_state=active_state,
        )

        # Inject tool definitions into system prompt (non-guests only)
        tool_registry = ctx.ports.get("tool_registry")
        if tool_registry and isinstance(tool_registry, ToolRegistry) and not is_guest:
            system_prompt += tool_registry.get_tool_prompt_block()

        # 2. Short-Term Conversation History (unchanged logic)
        user_id = ctx.user_id or "unknown"
        db = getattr(memory_port, "persistence", None) if memory_port else None
        from packages.core.memory.persistence import PersistenceContext

        if db and not isinstance(db, PersistenceContext):
            db = None

        if db:
            history = self._db_get_history(db, user_id)
            if history and self._is_db_session_expired(history):
                self._db_clear_history(db, user_id)
                history = []
        else:
            history = self._get_or_create_history(user_id)
            if history and self._is_session_expired(history):
                history.clear()

        prompt_str = self._context_builder.build_history_prompt(
            history, ctx.raw_text
        )

        try:
            response = await llm.generate(
                prompt_str,
                system=system_prompt,
            )

            # Check if the LLM wants to call a tool
            tool_executor = ctx.ports.get("tool_executor")
            if (
                tool_executor
                and isinstance(tool_executor, ToolExecutor)
                and tool_executor.is_tool_call(response)
            ):
                response = await tool_executor.execute(
                    response,
                    user_role=ctx.user_role or "unknown",
                    user_id=user_id,
                    language=getattr(ctx, "language", "en") or "en",
                )

            # Persist this exchange
            if db:
                self._db_save_turn(db, user_id, "user", ctx.raw_text)
                self._db_save_turn(db, user_id, "assistant", response)
                max_entries = _MAX_HISTORY_TURNS * 2
                self._db_trim_history(db, user_id, max_entries)
            else:
                history.append(_ConversationTurn("user", ctx.raw_text))
                history.append(_ConversationTurn("assistant", response))
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

    # ── DB session history helpers ──

    def _db_get_history(self, db, user_id: str) -> list[_ConversationTurn]:
        """Load history from the database."""
        with db.get_connection() as conn:
            rows = conn.execute(
                """
                SELECT role, content, timestamp 
                FROM conversation_history 
                WHERE user_id = ? 
                ORDER BY id ASC
                """,
                (user_id,)
            ).fetchall()

        history = []
        for role, content, timestamp in rows:
            turn = _ConversationTurn(role, content)
            turn.timestamp = timestamp
            history.append(turn)
        return history

    def _db_save_turn(self, db, user_id: str, role: str, content: str) -> None:
        """Save a single conversation turn to the database."""
        import time

        with db.get_connection() as conn:
            conn.execute(
                """
                INSERT INTO conversation_history (user_id, role, content, timestamp)
                VALUES (?, ?, ?, ?)
                """,
                (user_id, role, content, time.time()),
            )
            conn.commit()

    def _db_clear_history(self, db, user_id: str) -> None:
        """Wipe history for a user in the database."""
        with db.get_connection() as conn:
            conn.execute(
                "DELETE FROM conversation_history WHERE user_id = ?",
                (user_id,),
            )
            conn.commit()

    def _db_trim_history(self, db, user_id: str, max_entries: int) -> None:
        """Keep only the last max_entries turns for a user in the database."""
        with db.get_connection() as conn:
            conn.execute(
                """
                DELETE FROM conversation_history 
                WHERE user_id = ? AND id NOT IN (
                    SELECT id FROM conversation_history 
                    WHERE user_id = ? 
                    ORDER BY id DESC 
                    LIMIT ?
                )
                """,
                (user_id, user_id, max_entries),
            )
            conn.commit()

    def _is_db_session_expired(self, history: list[_ConversationTurn]) -> bool:
        """True if the last turn is older than the session timeout."""
        if not history:
            return False
        import time

        elapsed = time.time() - history[-1].timestamp
        return elapsed > self._session_timeout_s

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
