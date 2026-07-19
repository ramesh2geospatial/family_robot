"""
Unit tests for the JourneyAuditSkill.
"""

from __future__ import annotations

from unittest.mock import MagicMock
import pytest

from packages.core.skills.base import SkillContext
from packages.core.skills.journey_audit.skill import JourneyAuditSkill

@pytest.mark.unit
class TestJourneyAuditSkill:

    @pytest.fixture
    def skill(self) -> JourneyAuditSkill:
        return JourneyAuditSkill()

    @pytest.mark.asyncio
    async def test_hear_query_success(self, skill: JourneyAuditSkill) -> None:
        mock_conv_logger = MagicMock()
        mock_conv_logger.get_recent.return_value = [
            {"user_id": "parent_default", "input_text": "turn on geyser"},
            {"user_id": "parent_default", "input_text": "what did you hear"}
        ]

        ctx = SkillContext(
            raw_text="what did you hear",
            language="en",
            user_id="parent_default",
            ports={"conversation_logger": mock_conv_logger}
        )

        result = await skill.execute(ctx)
        assert result.success is True
        assert "turn on geyser" in result.spoken_response
        assert "Before this, I heard you say" in result.spoken_response

    @pytest.mark.asyncio
    async def test_hear_query_hindi(self, skill: JourneyAuditSkill) -> None:
        mock_conv_logger = MagicMock()
        mock_conv_logger.get_recent.return_value = [
            {"user_id": "parent_default", "input_text": "गीजर चालू करो"},
            {"user_id": "parent_default", "input_text": "तुमने क्या सुना"}
        ]

        ctx = SkillContext(
            raw_text="तुमने क्या सुना",
            language="hi",
            user_id="parent_default",
            ports={"conversation_logger": mock_conv_logger}
        )

        result = await skill.execute(ctx)
        assert result.success is True
        assert "पिछली बार मैंने सुना: गीजर चालू करो" in result.spoken_response

    @pytest.mark.asyncio
    async def test_deny_query_success(self, skill: JourneyAuditSkill) -> None:
        mock_audit_log = MagicMock()
        mock_audit_log.read_recent.return_value = [
            {
                "event": "acl_check",
                "user_id": "child_default",
                "user_role": "child",
                "allowed": False,
                "details": {"intent": "control_geyser"}
            }
        ]

        ctx = SkillContext(
            raw_text="why was my request denied",
            language="en",
            user_id="child_default",
            ports={"audit_log": mock_audit_log}
        )

        result = await skill.execute(ctx)
        assert result.success is True
        assert "denied" in result.spoken_response.lower()
        assert "child" in result.spoken_response.lower()
        assert "geyser" in result.spoken_response.lower()

    @pytest.mark.asyncio
    async def test_deny_query_marathi(self, skill: JourneyAuditSkill) -> None:
        mock_audit_log = MagicMock()
        mock_audit_log.read_recent.return_value = [
            {
                "event": "acl_check",
                "user_id": "child_default",
                "user_role": "child",
                "allowed": False,
                "details": {"intent": "control_geyser"}
            }
        ]

        ctx = SkillContext(
            raw_text="माझा विनंती का नाकारली",
            language="mr",
            user_id="child_default",
            ports={"audit_log": mock_audit_log}
        )

        result = await skill.execute(ctx)
        assert result.success is True
        assert "नाकारण्यात आली" in result.spoken_response
        assert "child" in result.spoken_response

    @pytest.mark.asyncio
    async def test_command_query_success(self, skill: JourneyAuditSkill) -> None:
        mock_audit_log = MagicMock()
        mock_audit_log.read_recent.return_value = [
            {
                "event": "webapp_device_command",
                "user_id": "parent_default",
                "allowed": True,
                "details": {"device_id": "living room_light", "action": "on"}
            },
            {
                "event": "acl_check",
                "user_id": "parent_default",
                "allowed": True,
                "details": {"intent": "control_ac"}
            }
        ]

        ctx = SkillContext(
            raw_text="show my recent commands",
            language="en",
            user_id="parent_default",
            ports={"audit_log": mock_audit_log}
        )

        result = await skill.execute(ctx)
        assert result.success is True
        assert "recent successful actions" in result.spoken_response
        assert "on living room_light" in result.spoken_response
        assert "ac" in result.spoken_response

    @pytest.mark.asyncio
    async def test_no_ports(self, skill: JourneyAuditSkill) -> None:
        ctx = SkillContext(raw_text="what did you hear", ports={})
        result = await skill.execute(ctx)
        assert result.success is False
