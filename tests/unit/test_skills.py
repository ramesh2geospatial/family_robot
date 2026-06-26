"""
Unit tests for the skills package.
"""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from packages.core.skills.assistant.skill import AssistantSkill
from packages.core.skills.base import SkillContext, SkillResult
from packages.core.skills.lights.skill import LightsSkill
from packages.core.skills.memory_admin.skill import MemoryAdminSkill
from packages.core.skills.registry import SkillRegistry
from packages.core.skills.reminders.skill import RemindersSkill


# ──────────────────────────────────────────────
# Lights Skill
# ──────────────────────────────────────────────

@pytest.mark.unit
class TestLightsSkill:

    @pytest.fixture
    def skill(self) -> LightsSkill:
        return LightsSkill()

    @pytest.fixture
    def mock_home(self) -> AsyncMock:
        home = AsyncMock()
        home.set_switch = AsyncMock(return_value=True)
        home.set_level = AsyncMock(return_value=True)
        return home

    @pytest.mark.asyncio
    async def test_turn_on_light(self, skill: LightsSkill, mock_home) -> None:
        ctx = SkillContext(
            slots={"action": "on", "room": "living room"},
            ports={"home": mock_home},
        )
        result = await skill.execute(ctx)
        assert result.success is True
        assert "on" in result.spoken_response.lower()
        mock_home.set_switch.assert_called_once_with("living room_light", True)

    @pytest.mark.asyncio
    async def test_turn_off_light(self, skill: LightsSkill, mock_home) -> None:
        ctx = SkillContext(
            slots={"action": "off", "room": "bedroom"},
            ports={"home": mock_home},
        )
        result = await skill.execute(ctx)
        assert "off" in result.spoken_response.lower()
        mock_home.set_switch.assert_called_once_with("bedroom_light", False)

    @pytest.mark.asyncio
    async def test_dim_light(self, skill: LightsSkill, mock_home) -> None:
        ctx = SkillContext(
            slots={"action": "dim", "room": "hall", "pct": 50},
            ports={"home": mock_home},
        )
        result = await skill.execute(ctx)
        assert "50" in result.spoken_response
        mock_home.set_level.assert_called_once_with("hall_light", 50)

    @pytest.mark.asyncio
    async def test_no_home_port(self, skill: LightsSkill) -> None:
        ctx = SkillContext(slots={"action": "on"}, ports={})
        result = await skill.execute(ctx)
        assert result.success is False

    def test_skill_metadata(self, skill: LightsSkill) -> None:
        assert skill.name == "lights"
        assert "control_lights" in skill.required_permissions


# ──────────────────────────────────────────────
# Reminders Skill
# ──────────────────────────────────────────────

@pytest.mark.unit
class TestRemindersSkill:

    @pytest.fixture
    def skill(self) -> RemindersSkill:
        return RemindersSkill()

    @pytest.mark.asyncio
    async def test_set_reminder(self, skill: RemindersSkill) -> None:
        ctx = SkillContext(
            slots={"action": "set", "task": "buy milk"},
            raw_text="remind me to buy milk",
        )
        result = await skill.execute(ctx)
        assert result.success is True
        assert "buy milk" in result.spoken_response

    @pytest.mark.asyncio
    async def test_list_reminders_empty(self, skill: RemindersSkill) -> None:
        ctx = SkillContext(slots={"action": "list"})
        result = await skill.execute(ctx)
        assert "no active" in result.spoken_response.lower()

    @pytest.mark.asyncio
    async def test_set_then_list(self, skill: RemindersSkill) -> None:
        await skill.execute(SkillContext(slots={"action": "set", "task": "cook dinner"}))
        ctx = SkillContext(slots={"action": "list"})
        result = await skill.execute(ctx)
        assert "cook dinner" in result.spoken_response

    @pytest.mark.asyncio
    async def test_cancel_reminder(self, skill: RemindersSkill) -> None:
        await skill.execute(SkillContext(slots={"action": "set", "task": "task1"}))
        ctx = SkillContext(slots={"action": "cancel"})
        result = await skill.execute(ctx)
        assert "cancelled" in result.spoken_response.lower()

    @pytest.mark.asyncio
    async def test_cancel_empty(self, skill: RemindersSkill) -> None:
        ctx = SkillContext(slots={"action": "cancel"})
        result = await skill.execute(ctx)
        assert "no reminders" in result.spoken_response.lower()


# ──────────────────────────────────────────────
# Memory Admin Skill
# ──────────────────────────────────────────────

@pytest.mark.unit
class TestMemoryAdminSkill:

    @pytest.fixture
    def skill(self) -> MemoryAdminSkill:
        return MemoryAdminSkill()

    @pytest.fixture
    def mock_memory(self) -> AsyncMock:
        mem = AsyncMock()
        mem.store = AsyncMock(return_value="abcd1234-0000")
        mem.search = AsyncMock(return_value=[
            {"id": "abcd1234", "text": "Aarav birthday March 5", "score": 0.95}
        ])
        mem.delete = AsyncMock(return_value=True)
        return mem

    @pytest.mark.asyncio
    async def test_store(self, skill: MemoryAdminSkill, mock_memory) -> None:
        ctx = SkillContext(
            user_id="u1",
            slots={"action": "store", "fact": "Aarav birthday March 5"},
            ports={"memory": mock_memory},
        )
        result = await skill.execute(ctx)
        assert "remember" in result.spoken_response.lower()
        mock_memory.store.assert_called_once()

    @pytest.mark.asyncio
    async def test_recall(self, skill: MemoryAdminSkill, mock_memory) -> None:
        ctx = SkillContext(
            slots={"action": "recall", "query": "Aarav birthday"},
            ports={"memory": mock_memory},
        )
        result = await skill.execute(ctx)
        assert "March 5" in result.spoken_response

    @pytest.mark.asyncio
    async def test_recall_empty(self, skill: MemoryAdminSkill) -> None:
        mem = AsyncMock()
        mem.search = AsyncMock(return_value=[])
        ctx = SkillContext(
            slots={"action": "recall", "query": "xyz"},
            ports={"memory": mem},
        )
        result = await skill.execute(ctx)
        assert "don't have" in result.spoken_response.lower()

    @pytest.mark.asyncio
    async def test_forget(self, skill: MemoryAdminSkill, mock_memory) -> None:
        ctx = SkillContext(
            slots={"action": "forget", "query": "birthday"},
            ports={"memory": mock_memory},
        )
        result = await skill.execute(ctx)
        assert "forgotten" in result.spoken_response.lower()
        mock_memory.delete.assert_called_once()

    @pytest.mark.asyncio
    async def test_no_memory_port(self, skill: MemoryAdminSkill) -> None:
        ctx = SkillContext(slots={"action": "store"}, ports={})
        result = await skill.execute(ctx)
        assert result.success is False


# ──────────────────────────────────────────────
# Assistant Skill
# ──────────────────────────────────────────────

@pytest.mark.unit
class TestAssistantSkill:

    @pytest.fixture
    def skill(self) -> AssistantSkill:
        return AssistantSkill()

    @pytest.mark.asyncio
    async def test_chat(self, skill: AssistantSkill) -> None:
        llm = AsyncMock()
        llm.generate = AsyncMock(return_value="Here's a joke for you!")
        ctx = SkillContext(
            raw_text="tell me a joke",
            ports={"llm": llm},
        )
        result = await skill.execute(ctx)
        assert "joke" in result.spoken_response.lower()

    @pytest.mark.asyncio
    async def test_no_llm(self, skill: AssistantSkill) -> None:
        ctx = SkillContext(raw_text="hello", ports={})
        result = await skill.execute(ctx)
        assert result.success is False

    @pytest.mark.asyncio
    async def test_llm_error(self, skill: AssistantSkill) -> None:
        llm = AsyncMock()
        llm.generate = AsyncMock(side_effect=RuntimeError("OOM"))
        ctx = SkillContext(raw_text="hello", ports={"llm": llm})
        result = await skill.execute(ctx)
        assert result.success is False


# ──────────────────────────────────────────────
# Skill Registry
# ──────────────────────────────────────────────

@pytest.mark.unit
class TestSkillRegistry:

    def test_register_and_lookup(self) -> None:
        registry = SkillRegistry()
        lights = LightsSkill()
        registry.register(lights, ["home_control"])
        assert registry.get_skill("home_control") is lights

    def test_unregistered_returns_none(self) -> None:
        registry = SkillRegistry()
        assert registry.get_skill("nonexistent") is None

    def test_list_skills(self) -> None:
        registry = SkillRegistry()
        registry.register(LightsSkill(), ["home_control"])
        registry.register(RemindersSkill(), ["timer", "reminder"])
        names = registry.list_skills()
        assert "lights" in names
        assert "reminders" in names
