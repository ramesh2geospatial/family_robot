import logging

from packages.core.skills.base import BaseSkill, SkillContext, SkillResult

logger = logging.getLogger(__name__)

class MusicSkill(BaseSkill):
    """
    Skill to play/pause/skip music.
    """

    @property
    def name(self) -> str:
        return "music"

    @property
    def required_permissions(self) -> list[str]:
        return ["play_music"]

    async def execute(self, ctx: SkillContext) -> SkillResult:
        action = ctx.slots.get("action", "play")
        song = ctx.slots.get("song")

        if song:
            logger.info(f"[MusicPlayer] Playing song: {song}")
            return SkillResult(
                spoken_response=f"Playing {song}.",
                success=True,
                memory_item=f"Music playing: {song}"
            )

        if action in ("pause", "stop"):
            logger.info("[MusicPlayer] Music paused/stopped.")
            return SkillResult(spoken_response="I have stopped the music.", success=True)

        if action == "next":
            logger.info("[MusicPlayer] Skipping to next track.")
            return SkillResult(spoken_response="Skipping to the next track.", success=True)

        return SkillResult(spoken_response="I'm not sure how to control the music.", success=False)
