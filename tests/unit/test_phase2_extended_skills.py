"""
Unit and integration tests for extended Phase 2 skills (fan, music, cooking, homework).
"""

from unittest.mock import AsyncMock

import pytest

from packages.core.cognition.intent_router import IntentRouter
from packages.core.governance.acl import ACL
from packages.core.governance.identity import FamilyMember, Role
from packages.core.skills.base import SkillContext
from packages.core.skills.cooking.skill import CookingSkill
from packages.core.skills.fan.skill import FanSkill
from packages.core.skills.homework.skill import HomeworkSkill
from packages.core.skills.music.skill import MusicSkill

# ──────────────────────────────────────────────
# Intent Router Parsing Tests
# ──────────────────────────────────────────────


@pytest.mark.unit
class TestExtendedIntentParsing:
    @pytest.mark.asyncio
    async def test_fan_intent(self) -> None:
        router = IntentRouter()
        intent = await router.classify("set fan speed to 3")
        assert intent.name == "control_fan"
        assert intent.entities.get("speed") == 3

    @pytest.mark.asyncio
    async def test_music_intent(self) -> None:
        router = IntentRouter()
        intent = await router.classify("play Dil Chahta Hai")
        assert intent.name == "play_music"
        assert intent.entities.get("action") == "play"
        assert intent.entities.get("song") == "Dil Chahta Hai"

        intent2 = await router.classify("pause music")
        assert intent2.name == "play_music"
        assert intent2.entities.get("action") == "pause"

    @pytest.mark.asyncio
    async def test_cooking_intent(self) -> None:
        router = IntentRouter()
        intent = await router.classify("convert 3 cups to ml")
        assert intent.name == "cooking"
        assert intent.entities.get("intent_id") == "cooking.convert"
        assert intent.entities.get("amount") == "3"
        assert intent.entities.get("unit") == "cups"
        assert intent.entities.get("target_unit") == "ml"

        intent2 = await router.classify("recipe for dal tadka")
        assert intent2.name == "cooking"
        assert intent2.entities.get("intent_id") == "cooking.recipe"
        assert intent2.entities.get("recipe") == "dal tadka"

        intent3 = await router.classify("next step")
        assert intent3.name == "cooking"
        assert intent3.entities.get("intent_id") == "cooking.next"

    @pytest.mark.asyncio
    async def test_homework_intent(self) -> None:
        router = IntentRouter()
        intent = await router.classify("explain gravity for grade 7")
        assert intent.name == "homework"
        assert intent.entities.get("intent_id") == "homework.explain"
        assert intent.entities.get("concept") == "gravity"
        assert intent.entities.get("grade") == "7"

        intent2 = await router.classify("solve 2x + 5 = 15")
        assert intent2.name == "homework"
        assert intent2.entities.get("intent_id") == "homework.solve"
        assert intent2.entities.get("problem") == "2x + 5 = 15"

        intent3 = await router.classify("quiz me on biology")
        assert intent3.name == "homework"
        assert intent3.entities.get("intent_id") == "homework.quiz"
        assert intent3.entities.get("topic") == "biology"


# ──────────────────────────────────────────────
# ACL Verification Tests
# ──────────────────────────────────────────────


@pytest.mark.unit
class TestExtendedACL:
    @pytest.fixture
    def acl(self) -> ACL:
        return ACL()

    def test_everyone_access(self, acl: ACL) -> None:
        child = FamilyMember(user_id="c1", name="Arjun", role=Role.CHILD)
        guest = FamilyMember(user_id="g1", name="Rohan", role=Role.GUEST)

        # All extended intents allowed for everyone
        assert acl.check_intent(child, "control_fan").allowed is True
        assert acl.check_intent(guest, "control_fan").allowed is True
        assert acl.check_intent(child, "play_music").allowed is True
        assert acl.check_intent(child, "cooking").allowed is True
        assert acl.check_intent(child, "homework").allowed is True


# ──────────────────────────────────────────────
# Skill Execution Tests
# ──────────────────────────────────────────────


@pytest.mark.unit
class TestExtendedSkills:
    @pytest.mark.asyncio
    async def test_fan_skill(self) -> None:
        mock_home = AsyncMock()
        mock_home.set_level = AsyncMock(return_value=True)
        mock_home.set_switch = AsyncMock(return_value=True)

        skill = FanSkill()
        ctx = SkillContext(slots={"speed": "3"}, ports={"home": mock_home})
        result = await skill.execute(ctx)
        assert result.success is True
        assert "speed to 3" in result.spoken_response
        mock_home.set_level.assert_called_once_with("fan", 60)

    @pytest.mark.asyncio
    async def test_music_skill(self) -> None:
        skill = MusicSkill()
        ctx = SkillContext(slots={"song": "Vande Mataram"}, ports={})
        result = await skill.execute(ctx)
        assert result.success is True
        assert "Vande Mataram" in result.spoken_response

    @pytest.mark.asyncio
    async def test_cooking_skill_recipe_flow(self) -> None:
        skill = CookingSkill()
        ctx_start = SkillContext(
            slots={"intent_id": "cooking.recipe", "recipe": "dal tadka"}, ports={}
        )
        res_start = await skill.execute(ctx_start)
        assert res_start.success is True
        assert "dal tadka" in res_start.spoken_response

        ctx_next = SkillContext(slots={"intent_id": "cooking.next"}, ports={})
        res_next = await skill.execute(ctx_next)
        assert res_next.success is True
        assert "Heat ghee" in res_next.spoken_response

    @pytest.mark.asyncio
    async def test_cooking_skill_convert(self) -> None:
        skill = CookingSkill()
        ctx = SkillContext(
            slots={
                "intent_id": "cooking.convert",
                "amount": "2",
                "unit": "cup",
                "target_unit": "ml",
            },
            ports={},
        )
        result = await skill.execute(ctx)
        assert result.success is True
        assert "480" in result.spoken_response

    @pytest.mark.asyncio
    async def test_homework_skill_llm(self) -> None:
        mock_llm = AsyncMock()
        mock_llm.generate = AsyncMock(return_value="Gravity pulls things down.")

        skill = HomeworkSkill()
        ctx = SkillContext(
            slots={"intent_id": "homework.explain", "concept": "gravity", "grade": "5"},
            ports={"llm": mock_llm},
        )
        result = await skill.execute(ctx)
        assert result.success is True
        assert "Gravity pulls" in result.spoken_response
