"""
Skill discovery and registry.

Maps intent names to concrete skill instances so the orchestrator
can route classified intents to the correct handler.
"""

from __future__ import annotations

import logging
from typing import Optional

from packages.core.skills.base import BaseSkill

logger = logging.getLogger(__name__)


class SkillRegistry:
    """Registry that maps intent names → skill instances."""

    def __init__(self) -> None:
        self._skills: dict[str, BaseSkill] = {}
        self._intent_map: dict[str, BaseSkill] = {}

    def register(self, skill: BaseSkill, intents: list[str]) -> None:
        """Register *skill* to handle the given *intents*."""
        self._skills[skill.name] = skill
        for intent in intents:
            self._intent_map[intent] = skill
            logger.info("Registered skill '%s' for intent '%s'", skill.name, intent)

    def get_skill(self, intent_name: str) -> Optional[BaseSkill]:
        """Return the skill registered for *intent_name*, or None."""
        return self._intent_map.get(intent_name)

    def list_skills(self) -> list[str]:
        """Return all registered skill names."""
        return list(self._skills.keys())
