"""
Unit and integration tests for Phase 3 capabilities.
"""

import asyncio
import json
from unittest.mock import AsyncMock

import pytest

from packages.adapters.android.telephony import TermuxTelephonyAdapter
from packages.adapters.desktop.telephony import DesktopTelephonyAdapter
from packages.adapters.raspberrypi.telephony import PiTelephonyAdapter
from packages.core.cognition.intent_router import IntentRouter
from packages.core.governance.identity import FamilyMember, IdentityStore, Role
from packages.core.ports.telephony import TelephonyPort
from packages.core.skills.base import SkillContext
from packages.core.skills.calls.skill import CallsSkill
from packages.core.skills.security.skill import SecuritySkill
from packages.core.skills.sensors.skill import SensorsSkill

# ──────────────────────────────────────────────
# Telephony Adapter Tests
# ──────────────────────────────────────────────


@pytest.mark.unit
class TestTelephonyAdapters:
    @pytest.mark.asyncio
    async def test_desktop_telephony(self) -> None:
        adapter = DesktopTelephonyAdapter()
        assert await adapter.make_call("+919876543210") is True
        assert await adapter.open_whatsapp("+919876543210", "hello") is True

    @pytest.mark.asyncio
    async def test_android_telephony_mock(self) -> None:
        adapter = TermuxTelephonyAdapter()
        # Shutil.which will not find Termux CLI commands on windows development environments, so mock path triggers
        assert await adapter.make_call("+919876543210") is True
        assert await adapter.open_whatsapp("+919876543210", "hello") is True

    @pytest.mark.asyncio
    async def test_pi_telephony_relays(self) -> None:
        mock_mqtt = AsyncMock()
        mock_mqtt.is_connected = True
        mock_mqtt.publish = AsyncMock(return_value=True)

        adapter = PiTelephonyAdapter(mqtt_client=mock_mqtt)
        assert await adapter.make_call("+919876543210") is True
        mock_mqtt.publish.assert_called_once_with(
            "familyrobot/android/telephony/call", "+919876543210"
        )


# ──────────────────────────────────────────────
# Intent Router Tests
# ──────────────────────────────────────────────


@pytest.mark.unit
class TestPhase3Intents:
    @pytest.mark.asyncio
    async def test_calls_intent_rule(self) -> None:
        router = IntentRouter()
        intent = await router.classify("call Ramesh")
        assert intent.name == "calls"
        assert intent.entities.get("contact") == "Ramesh"

    @pytest.mark.asyncio
    async def test_security_intent_rule(self) -> None:
        router = IntentRouter()
        intent = await router.classify("check security")
        assert intent.name == "security"

    @pytest.mark.asyncio
    async def test_sensors_intent_rule(self) -> None:
        router = IntentRouter()
        intent = await router.classify("sensor status")
        assert intent.name == "sensors"


# ──────────────────────────────────────────────
# Calls Skill Tests
# ──────────────────────────────────────────────


@pytest.mark.unit
class TestCallsSkill:
    @pytest.fixture
    def skill(self) -> CallsSkill:
        return CallsSkill()

    @pytest.fixture
    def identity_store(self) -> IdentityStore:
        store = IdentityStore()
        store.enroll(FamilyMember(user_id="u1", name="Ramesh", role=Role.PARENT))
        return store

    @pytest.mark.asyncio
    async def test_call_whitelisted_contact(
        self, skill: CallsSkill, identity_store
    ) -> None:
        mock_telephony = AsyncMock(spec=TelephonyPort)
        mock_telephony.make_call = AsyncMock(return_value=True)

        ctx = SkillContext(
            slots={"contact": "Ramesh"},
            ports={"identity_store": identity_store, "telephony": mock_telephony},
        )
        result = await skill.execute(ctx)
        assert result.success is True
        assert "calling Ramesh" in result.spoken_response
        mock_telephony.make_call.assert_called_once()

    @pytest.mark.asyncio
    async def test_call_unregistered_contact(
        self, skill: CallsSkill, identity_store
    ) -> None:
        mock_telephony = AsyncMock(spec=TelephonyPort)
        ctx = SkillContext(
            slots={"contact": "UnknownPerson"},
            ports={"identity_store": identity_store, "telephony": mock_telephony},
        )
        result = await skill.execute(ctx)
        assert result.success is False
        assert "only call enrolled family members" in result.spoken_response
        mock_telephony.make_call.assert_not_called()


# ──────────────────────────────────────────────
# Security Skill Tests
# ──────────────────────────────────────────────


@pytest.mark.unit
class TestSecuritySkill:
    @pytest.fixture
    def skill(self) -> SecuritySkill:
        return SecuritySkill()

    @pytest.fixture
    def identity_store(self) -> IdentityStore:
        return IdentityStore()

    @pytest.mark.asyncio
    async def test_security_check_unknown_face(
        self, skill: SecuritySkill, identity_store
    ) -> None:
        mock_camera = AsyncMock()
        mock_camera.capture = AsyncMock(return_value=b"image_bytes")
        mock_notify = AsyncMock()
        mock_notify.push = AsyncMock(return_value=None)

        ctx = SkillContext(
            ports={
                "camera": mock_camera,
                "notify": mock_notify,
                "identity_store": identity_store,
            }
        )
        result = await skill.execute(ctx)
        assert result.success is True
        assert "detected an unknown face" in result.spoken_response.lower()
        mock_notify.push.assert_called_once_with(
            user_id="parent_default",
            title="SECURITY ALERT",
            body="Unknown face detected at night!",
        )


# ──────────────────────────────────────────────
# Sensors Skill Tests
# ──────────────────────────────────────────────


@pytest.mark.unit
class TestSensorsSkill:
    @pytest.fixture
    def skill(self) -> SensorsSkill:
        return SensorsSkill()

    @pytest.mark.asyncio
    async def test_sensors_initial_status(self, skill: SensorsSkill) -> None:
        ctx = SkillContext()
        result = await skill.execute(ctx)
        assert result.success is True
        assert "closed" in result.spoken_response
        assert "clear" in result.spoken_response

    @pytest.mark.asyncio
    async def test_sensors_mqtt_door_open(self, skill: SensorsSkill) -> None:
        # Simulate open door message
        payload = json.dumps({"contact": False})
        skill.handle_mqtt_message("zigbee2mqtt/front_door", payload, {})

        ctx = SkillContext()
        result = await skill.execute(ctx)
        assert "open" in result.spoken_response

    @pytest.mark.asyncio
    async def test_sensors_mqtt_smoke_alarm(self, skill: SensorsSkill) -> None:
        mock_notify = AsyncMock()
        payload = json.dumps({"smoke": True})
        skill.handle_mqtt_message(
            "zigbee2mqtt/kitchen_smoke", payload, {"notify": mock_notify}
        )

        # Yield control to let asyncio.create_task run the async push notify callback
        await asyncio.sleep(0.1)

        ctx = SkillContext()
        result = await skill.execute(ctx)
        assert "smoke detected" in result.spoken_response.lower()
        mock_notify.push.assert_called_once_with(
            user_id="parent_default",
            title="FIRE ALERT",
            body="Kitchen smoke sensor has triggered!",
        )
