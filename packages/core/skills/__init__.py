"""
Skills package: pluggable skill modules for FamilyRobot.
"""

from packages.core.skills.assistant.skill import AssistantSkill
from packages.core.skills.base import BaseSkill, SkillContext, SkillResult
from packages.core.skills.lights.skill import LightsSkill
from packages.core.skills.memory_admin.skill import MemoryAdminSkill
from packages.core.skills.registry import SkillRegistry
from packages.core.skills.reminders.skill import RemindersSkill

__all__ = [
    "AssistantSkill",
    "BaseSkill",
    "LightsSkill",
    "MemoryAdminSkill",
    "RemindersSkill",
    "SkillContext",
    "SkillRegistry",
    "SkillResult",
]
