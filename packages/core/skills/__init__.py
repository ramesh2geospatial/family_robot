"""
Skills package: pluggable skill modules for FamilyRobot.
"""

from packages.core.skills.assistant.skill import AssistantSkill
from packages.core.skills.base import BaseSkill, SkillContext, SkillResult
from packages.core.skills.calls.skill import CallsSkill
from packages.core.skills.lights.skill import LightsSkill
from packages.core.skills.memory_admin.skill import MemoryAdminSkill
from packages.core.skills.registry import SkillRegistry
from packages.core.skills.reminders.skill import RemindersSkill
from packages.core.skills.security.skill import SecuritySkill
from packages.core.skills.sensors.skill import SensorsSkill

__all__ = [
    "AssistantSkill",
    "BaseSkill",
    "LightsSkill",
    "MemoryAdminSkill",
    "RemindersSkill",
    "CallsSkill",
    "SecuritySkill",
    "SensorsSkill",
    "SkillContext",
    "SkillRegistry",
    "SkillResult",
]
