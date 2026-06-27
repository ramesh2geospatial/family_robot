import asyncio
import logging

from packages.core.skills.base import BaseSkill, SkillContext, SkillResult

logger = logging.getLogger(__name__)


async def auto_off_timer(home, device_name: str, delay_seconds: int) -> None:
    """
    Background safety task to automatically turn off mains device after a duration.
    """
    logger.info(
        f"[Safety Timer] Scheduled auto-off for {device_name} in {delay_seconds} seconds."
    )
    await asyncio.sleep(delay_seconds)
    try:
        ok = await home.set_switch(device_name, False)
        if ok:
            logger.info(f"[Safety Timer] Auto-off executed for {device_name}.")
        else:
            logger.error(
                f"[Safety Timer] Failed to execute auto-off switch for {device_name}."
            )
    except Exception as e:
        logger.error(f"[Safety Timer] Exception in auto-off execution: {e}")


class GeyserSkill(BaseSkill):
    """
    Skill to control geyser switch with auto-off safety timeout.
    """

    @property
    def name(self) -> str:
        return "geyser"

    @property
    def required_permissions(self) -> list[str]:
        return ["control_geyser"]

    async def execute(self, ctx: SkillContext) -> SkillResult:
        home = ctx.ports.get("home")
        if home is None:
            return SkillResult(
                spoken_response="Home control is not available.", success=False
            )

        action = ctx.slots.get("action", "on")
        on = action != "off"

        ok = await home.set_switch("geyser", on)
        if ok:
            if on:
                # Schedule safety shutdown after 20 minutes (using 1s in testing context, or config-driven)
                # For safety demo/testing, check if a delay override is in slots
                delay = int(
                    ctx.slots.get("auto_off_delay", 1200)
                )  # Default 20 mins (1200s)
                asyncio.create_task(auto_off_timer(home, "geyser", delay))
                return SkillResult(
                    spoken_response=f"I have turned on the geyser. It will automatically turn off in {delay // 60} minutes for safety.",
                    success=True,
                )
            else:
                return SkillResult(
                    spoken_response="I have turned off the geyser.", success=True
                )

        return SkillResult(
            spoken_response="Failed to control the geyser.", success=False
        )
