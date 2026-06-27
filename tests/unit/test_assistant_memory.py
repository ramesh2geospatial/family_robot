"""
Tests for AssistantSkill memory integration.

Covers:
- Short-term conversation history preservation
- Long-term RAG injection with correct score filtering
- Guest user RAG isolation (AGENTS.md security rule)
- Session timeout clearing stale history
- LRU eviction when user cap is exceeded
- Character budget truncation for history
"""

from unittest.mock import ANY, AsyncMock

import pytest

from packages.core.skills.assistant.skill import AssistantSkill
from packages.core.skills.base import SkillContext


def _ctx(
    user_id: str = "user_123",
    user_role: str = "parent",
    raw_text: str = "hello",
    ports: dict | None = None,
) -> SkillContext:
    """Helper to build a SkillContext quickly."""
    return SkillContext(
        user_id=user_id,
        user_role=user_role,
        user_name="Test",
        language="en",
        raw_text=raw_text,
        slots={},
        ports=ports or {},
    )


@pytest.mark.unit
class TestShortTermHistory:
    @pytest.mark.asyncio
    async def test_history_preserved_across_turns(self) -> None:
        """Verify that Turn 2 prompt includes Turn 1 context."""
        skill = AssistantSkill()
        llm = AsyncMock()
        llm.generate = AsyncMock(return_value="Reply 1")

        await skill.execute(_ctx(raw_text="hello", ports={"llm": llm}))
        llm.generate.assert_called_once_with("USER: hello", system=ANY)

        llm.generate.reset_mock()
        llm.generate.return_value = "Reply 2"
        await skill.execute(_ctx(raw_text="follow up", ports={"llm": llm}))
        prompt = llm.generate.call_args[0][0]
        assert "USER: hello" in prompt
        assert "ASSISTANT: Reply 1" in prompt
        assert "USER: follow up" in prompt

    @pytest.mark.asyncio
    async def test_history_per_user_isolation(self) -> None:
        """Different users get independent history."""
        skill = AssistantSkill()
        llm = AsyncMock()
        llm.generate = AsyncMock(return_value="ok")

        await skill.execute(
            _ctx(
                user_id="alice",
                raw_text="Alice says hi",
                ports={"llm": llm},
            )
        )
        llm.generate.reset_mock()
        await skill.execute(
            _ctx(
                user_id="bob",
                raw_text="Bob says hi",
                ports={"llm": llm},
            )
        )
        # Bob's prompt should NOT contain Alice's message
        prompt = llm.generate.call_args[0][0]
        assert "Alice says hi" not in prompt
        assert "USER: Bob says hi" in prompt


@pytest.mark.unit
class TestSessionTimeout:
    @pytest.mark.asyncio
    async def test_stale_history_cleared(self) -> None:
        """After session timeout, history is wiped."""
        import asyncio

        skill = AssistantSkill(session_timeout_s=0.01)
        llm = AsyncMock()
        llm.generate = AsyncMock(return_value="r1")

        await skill.execute(_ctx(raw_text="old msg", ports={"llm": llm}))
        # Wait long enough to exceed timeout
        await asyncio.sleep(0.02)
        llm.generate.reset_mock()
        llm.generate.return_value = "r2"
        await skill.execute(_ctx(raw_text="new msg", ports={"llm": llm}))
        prompt = llm.generate.call_args[0][0]
        # old msg should be cleared due to timeout
        assert "old msg" not in prompt
        assert "USER: new msg" in prompt


@pytest.mark.unit
class TestLRUEviction:
    @pytest.mark.asyncio
    async def test_oldest_user_evicted(self) -> None:
        """When max_users is exceeded, oldest user is evicted."""
        skill = AssistantSkill(max_users=2)
        llm = AsyncMock()
        llm.generate = AsyncMock(return_value="ok")

        # Fill slots for 2 users
        await skill.execute(_ctx(user_id="u1", raw_text="hi1", ports={"llm": llm}))
        await skill.execute(_ctx(user_id="u2", raw_text="hi2", ports={"llm": llm}))
        # Adding u3 should evict u1
        await skill.execute(_ctx(user_id="u3", raw_text="hi3", ports={"llm": llm}))
        assert "u1" not in skill._history
        assert "u2" in skill._history
        assert "u3" in skill._history


@pytest.mark.unit
class TestCharBudget:
    @pytest.mark.asyncio
    async def test_long_history_truncated(self) -> None:
        """History exceeding char budget drops oldest turns."""
        # Very tight budget: only ~50 chars for history
        skill = AssistantSkill(max_history_chars=50)
        llm = AsyncMock()
        llm.generate = AsyncMock(return_value="short")

        # Build up history
        for i in range(5):
            await skill.execute(
                _ctx(
                    raw_text=f"message number {i}",
                    ports={"llm": llm},
                )
            )

        llm.generate.reset_mock()
        llm.generate.return_value = "final"
        await skill.execute(_ctx(raw_text="latest query", ports={"llm": llm}))
        prompt = llm.generate.call_args[0][0]
        # The prompt should contain the current query
        assert "USER: latest query" in prompt
        # Total length (minus the current query line) should be
        # within the budget
        lines = prompt.split("\n")
        history_lines = lines[:-1]  # everything except current
        history_text = "\n".join(history_lines)
        assert len(history_text) <= 50 + 10  # small tolerance


@pytest.mark.unit
class TestRAGIntegration:
    @pytest.mark.asyncio
    async def test_high_score_facts_injected(self) -> None:
        """RAG facts with score >= 0.5 are injected into system prompt."""
        skill = AssistantSkill()
        llm = AsyncMock()
        llm.generate = AsyncMock(return_value="tea answer")
        memory = AsyncMock()
        memory.search = AsyncMock(
            return_value=[
                {"text": "Ramesh drinks black tea.", "score": 0.85},
            ]
        )

        await skill.execute(
            _ctx(
                raw_text="what do I drink?",
                ports={"llm": llm, "memory": memory},
            )
        )
        system = llm.generate.call_args[1]["system"]
        assert "Ramesh drinks black tea." in system

    @pytest.mark.asyncio
    async def test_low_score_facts_filtered(self) -> None:
        """RAG facts with score < 0.5 are NOT injected."""
        skill = AssistantSkill()
        llm = AsyncMock()
        llm.generate = AsyncMock(return_value="dunno")
        memory = AsyncMock()
        memory.search = AsyncMock(
            return_value=[
                {"text": "irrelevant fact", "score": 0.2},
            ]
        )

        await skill.execute(
            _ctx(
                raw_text="random q",
                ports={"llm": llm, "memory": memory},
            )
        )
        system = llm.generate.call_args[1]["system"]
        assert "irrelevant fact" not in system

    @pytest.mark.asyncio
    async def test_guest_no_rag(self) -> None:
        """Guest users must NOT receive RAG injection (security)."""
        skill = AssistantSkill()
        llm = AsyncMock()
        llm.generate = AsyncMock(return_value="hi guest")
        memory = AsyncMock()
        memory.search = AsyncMock(
            return_value=[
                {"text": "secret family fact", "score": 0.95},
            ]
        )

        await skill.execute(
            _ctx(
                user_role="guest",
                raw_text="tell me secrets",
                ports={"llm": llm, "memory": memory},
            )
        )
        # Memory should NOT have been queried at all
        memory.search.assert_not_called()
        system = llm.generate.call_args[1]["system"]
        assert "secret family fact" not in system

    @pytest.mark.asyncio
    async def test_memory_failure_graceful(self) -> None:
        """If memory search raises, skill still works."""
        skill = AssistantSkill()
        llm = AsyncMock()
        llm.generate = AsyncMock(return_value="still works")
        memory = AsyncMock()
        memory.search = AsyncMock(side_effect=RuntimeError("db locked"))

        res = await skill.execute(
            _ctx(
                raw_text="hi",
                ports={"llm": llm, "memory": memory},
            )
        )
        assert res.success is True
        assert res.spoken_response == "still works"
