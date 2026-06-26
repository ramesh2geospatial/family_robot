"""
Lights skill – on/off/dim via HomePort.
"""

from __future__ import annotations

import logging

from packages.core.skills.base import BaseSkill, SkillContext, SkillResult

logger = logging.getLogger(__name__)


class LightsSkill(BaseSkill):
    """Control lights via HomePort.set_switch / set_level."""

    @property
    def name(self) -> str:
        return "lights"

    @property
    def required_permissions(self) -> list[str]:
        return ["control_lights"]

    async def execute(self, ctx: SkillContext) -> SkillResult:
        home = ctx.ports.get("home")
        if home is None:
            return SkillResult(spoken_response="Home control is not available.", success=False)

        action = ctx.slots.get("action", "on")
        room = ctx.slots.get("room", "")
        device_id = f"{room}_light" if room else "light"
        pct = ctx.slots.get("pct")

        if pct is not None:
            # Dim
            try:
                pct_int = int(pct)
            except (ValueError, TypeError):
                return SkillResult(spoken_response="I didn't understand the brightness level.")
            ok = await home.set_level(device_id, pct_int)
            if ok:
                return SkillResult(
                    spoken_response=f"Set the {room + ' ' if room else ''}light to {pct_int} percent."
                )
            return SkillResult(spoken_response=f"Failed to dim the {room} light.", success=False)

        # On/Off
        on = action != "off"
        ok = await home.set_switch(device_id, on)
        state_word = "on" if on else "off"
        if ok:
            return SkillResult(
                spoken_response=f"Turned {state_word} the {room + ' ' if room else ''}light."
            )
        return SkillResult(
            spoken_response=f"Failed to turn {state_word} the light.", success=False
        )
