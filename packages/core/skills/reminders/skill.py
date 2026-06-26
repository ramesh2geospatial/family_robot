"""
Reminders skill – set, list, and cancel reminders.

Uses an in-memory store for the Desktop MVP. Future versions will
persist to SQLite and fire via asyncio scheduled tasks.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

from packages.core.skills.base import BaseSkill, SkillContext, SkillResult

logger = logging.getLogger(__name__)


@dataclass
class Reminder:
    """A single reminder entry."""

    id: str
    task: str
    created_at: str
    duration_seconds: Optional[int] = None
    fired: bool = False


class RemindersSkill(BaseSkill):
    """Set, list, and cancel reminders."""

    def __init__(self) -> None:
        self._reminders: list[Reminder] = []

    @property
    def name(self) -> str:
        return "reminders"

    @property
    def required_permissions(self) -> list[str]:
        return ["general_info"]

    async def execute(self, ctx: SkillContext) -> SkillResult:
        action = ctx.slots.get("action", "set")

        if action == "list":
            return self._list_reminders()
        if action == "cancel":
            return self._cancel_last()
        return self._set_reminder(ctx)

    def _set_reminder(self, ctx: SkillContext) -> SkillResult:
        task = ctx.slots.get("task", ctx.raw_text)
        duration = ctx.slots.get("duration")

        reminder = Reminder(
            id=str(uuid.uuid4()),
            task=task,
            created_at=datetime.now(timezone.utc).isoformat(),
            duration_seconds=duration.get("seconds", 0) if isinstance(duration, dict) else None,
        )
        self._reminders.append(reminder)
        logger.info("Reminder set: %s", task)

        if reminder.duration_seconds:
            minutes = reminder.duration_seconds // 60
            return SkillResult(
                spoken_response=f"I'll remind you in {minutes} minutes: {task}"
            )
        return SkillResult(spoken_response=f"Reminder set: {task}")

    def _list_reminders(self) -> SkillResult:
        active = [r for r in self._reminders if not r.fired]
        if not active:
            return SkillResult(spoken_response="You have no active reminders.")

        items = [f"{i+1}. {r.task}" for i, r in enumerate(active)]
        text = "Your reminders: " + "; ".join(items)
        return SkillResult(spoken_response=text)

    def _cancel_last(self) -> SkillResult:
        active = [r for r in self._reminders if not r.fired]
        if not active:
            return SkillResult(spoken_response="No reminders to cancel.")
        active[-1].fired = True
        return SkillResult(
            spoken_response=f"Cancelled reminder: {active[-1].task}"
        )
