"""
Base skill framework for FamilyRobot.

Defines the abstract base class, context, and result types that all
skills must implement.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Optional

logger = logging.getLogger(__name__)


@dataclass
class SkillContext:
    """Runtime context passed to every skill execution."""

    user_id: str = "unknown"
    user_role: str = "guest"
    user_name: str = "Someone"
    language: str = "en"
    raw_text: str = ""
    slots: dict = field(default_factory=dict)
    # Port references (injected by the orchestrator)
    ports: dict = field(default_factory=dict)


@dataclass
class SkillResult:
    """Returned by a skill after execution."""

    spoken_response: str
    success: bool = True
    memory_item: Optional[str] = None  # text to store in memory
    memory_meta: Optional[dict] = None


class BaseSkill(ABC):
    """Abstract base class for all FamilyRobot skills."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Short unique skill name, e.g. 'lights'."""
        ...

    @property
    @abstractmethod
    def required_permissions(self) -> list[str]:
        """Permission strings checked by ACL before execute()."""
        ...

    @abstractmethod
    async def execute(self, ctx: SkillContext) -> SkillResult:
        """Run the skill and return a spoken response."""
        ...
