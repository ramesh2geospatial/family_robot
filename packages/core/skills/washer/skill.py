import logging

from packages.core.skills.base import BaseSkill, SkillContext, SkillResult

logger = logging.getLogger(__name__)


class WasherSkill(BaseSkill):
    """
    Skill to control the washing machine power switch, verifying loads first.
    """

    @property
    def name(self) -> str:
        return "washer"

    @property
    def required_permissions(self) -> list[str]:
        return ["control_washer"]

    async def execute(self, ctx: SkillContext) -> SkillResult:
        home = ctx.ports.get("home")
        if home is None:
            return SkillResult(
                spoken_response="Home control is not available.", success=False
            )

        action = ctx.slots.get("action", "on")
        on = action != "off"

        ok = await home.set_switch("washer", on)
        if ok:
            if on:
                return SkillResult(
                    spoken_response="I have turned on the washing machine. Please make sure clothes and detergent are loaded before starting a cycle.",
                    success=True,
                )
            else:
                return SkillResult(
                    spoken_response="I have turned off the washing machine.",
                    success=True,
                )

        return SkillResult(
            spoken_response="Failed to control the washing machine.", success=False
        )
