import logging

from packages.core.skills.base import BaseSkill, SkillContext, SkillResult

logger = logging.getLogger(__name__)

class FanSkill(BaseSkill):
    """
    Skill to control fan power and speed.
    Maps speed levels 1-5 to 20%-100% HomePort.set_level.
    """

    @property
    def name(self) -> str:
        return "fan"

    @property
    def required_permissions(self) -> list[str]:
        return ["control_fan"]

    async def execute(self, ctx: SkillContext) -> SkillResult:
        home = ctx.ports.get("home")
        if home is None:
            return SkillResult(spoken_response="Home control is not available.", success=False)

        action = ctx.slots.get("action", "on")
        speed = ctx.slots.get("speed")

        responses = []

        if speed is not None:
            try:
                speed_val = int(speed)
            except (ValueError, TypeError):
                return SkillResult(spoken_response="I didn't understand the speed level.", success=False)

            # Map speed 1-5 to percentage
            if speed_val < 1 or speed_val > 5:
                return SkillResult(spoken_response="Fan speed must be between 1 and 5.", success=False)

            pct = speed_val * 20
            ok = await home.set_level("fan", pct)
            if ok:
                responses.append(f"Set the fan speed to {speed_val}.")
            else:
                responses.append("Failed to change the fan speed.")

        if speed is None:
            on = action != "off"
            ok = await home.set_switch("fan", on)
            state_word = "on" if on else "off"
            if ok:
                responses.append(f"Turned {state_word} the fan.")
            else:
                responses.append(f"Failed to turn {state_word} the fan.")

        spoken = " ".join(responses)
        return SkillResult(
            spoken_response=spoken,
            success="Failed" not in spoken
        )
