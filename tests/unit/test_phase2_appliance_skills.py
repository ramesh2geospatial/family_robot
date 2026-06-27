"""
Unit and integration tests for Phase 2 appliance control skills.
"""

import asyncio
from unittest.mock import AsyncMock

import pytest

from packages.core.cognition.intent_router import IntentRouter
from packages.core.governance.acl import ACL
from packages.core.governance.identity import FamilyMember, Role
from packages.core.skills.ac.skill import AcSkill
from packages.core.skills.base import SkillContext
from packages.core.skills.geyser.skill import GeyserSkill
from packages.core.skills.pump.skill import PumpSkill
from packages.core.skills.tv.skill import TvSkill
from packages.core.skills.washer.skill import WasherSkill

# ──────────────────────────────────────────────
# Intent Router Parsing Tests
# ──────────────────────────────────────────────


@pytest.mark.unit
class TestApplianceIntentParsing:
    @pytest.mark.asyncio
    async def test_ac_intent_temp_mode(self) -> None:
        router = IntentRouter()
        intent = await router.classify("set ac to 24 degrees in cool mode")
        assert intent.name == "control_ac"
        assert intent.entities.get("temp") == 24
        assert intent.entities.get("mode") == "cool"

    @pytest.mark.asyncio
    async def test_tv_intent_volume_source(self) -> None:
        router = IntentRouter()
        intent = await router.classify("volume up the tv")
        assert intent.name == "control_tv"
        assert intent.entities.get("action") == "volume_up"

        intent2 = await router.classify("change source on tv to HDMI1")
        assert intent2.name == "control_tv"
        assert intent2.entities.get("source") == "HDMI1"

    @pytest.mark.asyncio
    async def test_mains_appliances_intents(self) -> None:
        router = IntentRouter()
        assert (await router.classify("switch on the geyser")).name == "control_geyser"
        assert (await router.classify("turn off the water pump")).name == "control_pump"
        assert (await router.classify("turn on washer")).name == "control_washer"


# ──────────────────────────────────────────────
# ACL Role-Gating Tests
# ──────────────────────────────────────────────


@pytest.mark.unit
class TestApplianceACL:
    @pytest.fixture
    def acl(self) -> ACL:
        return ACL()

    def test_ac_tv_gating(self, acl: ACL) -> None:
        parent = FamilyMember(user_id="p1", name="Ramesh", role=Role.PARENT)
        teen = FamilyMember(user_id="t1", name="Arjun", role=Role.TEEN)

        # AC / TV: parent allowed, teen denied
        assert acl.check_intent(parent, "control_ac").allowed is True
        assert acl.check_intent(teen, "control_ac").allowed is False
        assert acl.check_intent(parent, "control_tv").allowed is True
        assert acl.check_intent(teen, "control_tv").allowed is False

    def test_mains_gating(self, acl: ACL) -> None:
        parent = FamilyMember(user_id="p1", name="Ramesh", role=Role.PARENT)
        teen = FamilyMember(user_id="t1", name="Arjun", role=Role.TEEN)
        child = FamilyMember(user_id="c1", name="Karan", role=Role.CHILD)

        # Geyser / Pump: parent allowed, teen/child denied
        assert acl.check_intent(parent, "control_geyser").allowed is True
        assert acl.check_intent(teen, "control_geyser").allowed is False

        # Washer: parent/teen allowed, child denied
        assert acl.check_intent(parent, "control_washer").allowed is True
        assert acl.check_intent(teen, "control_washer").allowed is True
        assert acl.check_intent(child, "control_washer").allowed is False


# ──────────────────────────────────────────────
# Skill Execution Tests
# ──────────────────────────────────────────────


@pytest.mark.unit
class TestApplianceSkills:
    @pytest.mark.asyncio
    async def test_ac_skill(self) -> None:
        mock_home = AsyncMock()
        mock_home.set_level = AsyncMock(return_value=True)
        mock_home.send_ir = AsyncMock(return_value=True)

        skill = AcSkill()
        ctx = SkillContext(
            slots={"temp": "24", "mode": "cool"}, ports={"home": mock_home}
        )
        result = await skill.execute(ctx)
        assert result.success is True
        assert "24" in result.spoken_response
        assert "cool" in result.spoken_response
        mock_home.set_level.assert_called_once_with("ac_temp", 24)
        mock_home.send_ir.assert_called_once_with("ac", "mode_cool")

    @pytest.mark.asyncio
    async def test_geyser_skill_timer(self) -> None:
        mock_home = AsyncMock()
        mock_home.set_switch = AsyncMock(return_value=True)

        skill = GeyserSkill()
        # Set 0s delay for testing auto_off trigger instantly
        ctx = SkillContext(
            slots={"action": "on", "auto_off_delay": 0}, ports={"home": mock_home}
        )
        result = await skill.execute(ctx)
        assert result.success is True
        assert "automatically turn off" in result.spoken_response
        mock_home.set_switch.assert_called_with("geyser", True)

        # Yield control to let background auto-off run and set geyser back to False
        await asyncio.sleep(0.01)
        mock_home.set_switch.assert_called_with("geyser", False)

    @pytest.mark.asyncio
    async def test_pump_skill_timer(self) -> None:
        mock_home = AsyncMock()
        mock_home.set_switch = AsyncMock(return_value=True)

        skill = PumpSkill()
        ctx = SkillContext(
            slots={"action": "on", "auto_off_delay": 0}, ports={"home": mock_home}
        )
        result = await skill.execute(ctx)
        assert result.success is True
        assert "prevent dry-running" in result.spoken_response
        mock_home.set_switch.assert_called_with("pump", True)

        await asyncio.sleep(0.01)
        mock_home.set_switch.assert_called_with("pump", False)

    @pytest.mark.asyncio
    async def test_washer_skill(self) -> None:
        mock_home = AsyncMock()
        mock_home.set_switch = AsyncMock(return_value=True)

        skill = WasherSkill()
        ctx = SkillContext(slots={"action": "on"}, ports={"home": mock_home})
        result = await skill.execute(ctx)
        assert result.success is True
        assert "make sure clothes and detergent are loaded" in result.spoken_response
        mock_home.set_switch.assert_called_once_with("washer", True)

    @pytest.mark.asyncio
    async def test_tv_skill(self) -> None:
        mock_home = AsyncMock()
        mock_home.send_ir = AsyncMock(return_value=True)
        mock_home.set_switch = AsyncMock(return_value=True)

        skill = TvSkill()
        ctx1 = SkillContext(slots={"action": "volume_up"}, ports={"home": mock_home})
        result1 = await skill.execute(ctx1)
        assert result1.success is True
        assert "Increased TV volume" in result1.spoken_response
        mock_home.send_ir.assert_called_with("tv", "volume_up")

        ctx2 = SkillContext(slots={"source": "HDMI2"}, ports={"home": mock_home})
        result2 = await skill.execute(ctx2)
        assert result2.success is True
        assert "HDMI2" in result2.spoken_response
        mock_home.send_ir.assert_called_with("tv", "source_HDMI2")
