import asyncio
import logging

from packages.core.skills.base import BaseSkill, SkillContext, SkillResult
from packages.core.skills.geyser.skill import auto_off_timer

logger = logging.getLogger(__name__)


class PumpSkill(BaseSkill):
    """
    Skill to control water pump switch with auto-off safety timeout.
    """

    @property
    def name(self) -> str:
        return "pump"

    @property
    def required_permissions(self) -> list[str]:
        return ["control_pump"]

    async def execute(self, ctx: SkillContext) -> SkillResult:
        home = ctx.ports.get("home")
        if home is None:
            return SkillResult(
                spoken_response="Home control is not available.", success=False
            )

        action = ctx.slots.get("action", "on")
        on = action != "off"

        ok = await home.set_switch("pump", on)
        if ok:
            if on:
                # Schedule safety shutdown after 15 minutes (900s)
                delay = int(
                    ctx.slots.get("auto_off_delay", 900)
                )  # Default 15 mins (900s)
                asyncio.create_task(auto_off_timer(home, "pump", delay))
                return SkillResult(
                    spoken_response=f"I have turned on the water pump. It will automatically turn off in {delay // 60} minutes to prevent dry-running.",
                    success=True,
                )
            else:
                return SkillResult(
                    spoken_response="I have turned off the water pump.", success=True
                )

        return SkillResult(
            spoken_response="Failed to control the water pump.", success=False
        )
