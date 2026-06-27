import logging

from packages.core.skills.base import BaseSkill, SkillContext, SkillResult

logger = logging.getLogger(__name__)


class TvSkill(BaseSkill):
    """
    Skill to control TV power, volume, and source switching via IR commands.
    """

    @property
    def name(self) -> str:
        return "tv"

    @property
    def required_permissions(self) -> list[str]:
        return ["control_tv"]

    async def execute(self, ctx: SkillContext) -> SkillResult:
        home = ctx.ports.get("home")
        if home is None:
            return SkillResult(
                spoken_response="Home control is not available.", success=False
            )

        action = ctx.slots.get("action", "on")
        source = ctx.slots.get("source")

        if source is not None:
            ok = await home.send_ir("tv", f"source_{source}")
            if ok:
                return SkillResult(
                    spoken_response=f"Changed TV source to {source}.", success=True
                )
            return SkillResult(
                spoken_response="Failed to change the TV source.", success=False
            )

        if "volume_up" in action or "volume up" in action:
            ok = await home.send_ir("tv", "volume_up")
            if ok:
                return SkillResult(spoken_response="Increased TV volume.", success=True)
            return SkillResult(
                spoken_response="Failed to increase TV volume.", success=False
            )

        if "volume_down" in action or "volume down" in action:
            ok = await home.send_ir("tv", "volume_down")
            if ok:
                return SkillResult(spoken_response="Decreased TV volume.", success=True)
            return SkillResult(
                spoken_response="Failed to decrease TV volume.", success=False
            )

        on = action != "off"
        ok = await home.set_switch("tv", on)
        state_word = "on" if on else "off"
        if ok:
            return SkillResult(
                spoken_response=f"Turned {state_word} the TV.", success=True
            )
        return SkillResult(
            spoken_response=f"Failed to turn {state_word} the TV.", success=False
        )
