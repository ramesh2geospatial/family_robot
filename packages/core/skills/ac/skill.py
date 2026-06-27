import logging

from packages.core.skills.base import BaseSkill, SkillContext, SkillResult

logger = logging.getLogger(__name__)


class AcSkill(BaseSkill):
    """
    Skill to control AC power, temperature, and modes via HomePort.
    """

    @property
    def name(self) -> str:
        return "ac"

    @property
    def required_permissions(self) -> list[str]:
        return ["control_ac"]

    async def execute(self, ctx: SkillContext) -> SkillResult:
        home = ctx.ports.get("home")
        if home is None:
            return SkillResult(
                spoken_response="Home control is not available.", success=False
            )

        action = ctx.slots.get("action", "on")
        temp = ctx.slots.get("temp")
        mode = ctx.slots.get("mode")

        responses = []

        # Temperature setting
        if temp is not None:
            try:
                temp_val = int(temp)
            except (ValueError, TypeError):
                return SkillResult(
                    spoken_response="I didn't understand the temperature level.",
                    success=False,
                )
            ok = await home.set_level("ac_temp", temp_val)
            if ok:
                responses.append(f"Set the AC temperature to {temp_val} degrees.")
            else:
                responses.append("Failed to set the AC temperature.")

        # Mode setting
        if mode is not None:
            ok = await home.send_ir("ac", f"mode_{mode}")
            if ok:
                responses.append(f"Set the AC mode to {mode}.")
            else:
                responses.append("Failed to set the AC mode.")

        # Power control (only run if temp/mode aren't specified, or if power action is explicit)
        if temp is None and mode is None:
            on = action != "off"
            ok = await home.set_switch("ac", on)
            state_word = "on" if on else "off"
            if ok:
                responses.append(f"Turned {state_word} the AC.")
            else:
                responses.append(f"Failed to turn {state_word} the AC.")

        spoken = " ".join(responses)
        return SkillResult(spoken_response=spoken, success="Failed" not in spoken)
