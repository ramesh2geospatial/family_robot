"""
Music skill for FamilyRobot.

Plays, pauses, stops, and skips music using the MediaPlayer port.
Falls back to browser if MediaPlayer is not available.
"""

import logging
import urllib.parse
import webbrowser

from packages.core.skills.base import BaseSkill, SkillContext, SkillResult

logger = logging.getLogger(__name__)


class MusicSkill(BaseSkill):
    """
    Skill to play/pause/skip music via the MediaPlayer port.
    """

    @property
    def name(self) -> str:
        return "music"

    @property
    def required_permissions(self) -> list[str]:
        return ["play_music"]

    async def execute(self, ctx: SkillContext) -> SkillResult:
        action = ctx.slots.get("action", "play")
        song = ctx.slots.get("song", "").strip()
        media_player = ctx.ports.get("media_player")

        # --- PLAY ---
        if action == "play":
            if media_player:
                try:
                    title = await media_player.play(song if song else "")
                    display_name = title or song or "some music"
                    logger.info("[MusicPlayer] Playing via mpv: %s", display_name)
                    return SkillResult(
                        spoken_response=f"Playing {display_name}.",
                        success=True,
                        memory_item=f"Music playing: {display_name}",
                    )
                except Exception as e:
                    logger.error("MediaPlayer.play() failed: %s", e)
                    # Fall through to browser fallback

            # Browser fallback
            return self._browser_play(song)

        # --- PAUSE / STOP ---
        if action in ("pause", "stop"):
            if media_player:
                try:
                    if action == "pause":
                        await media_player.pause()
                    else:
                        await media_player.stop()
                    logger.info("[MusicPlayer] Music %sed.", action)
                    return SkillResult(
                        spoken_response=f"I have {action}d the music.",
                        success=True,
                    )
                except Exception as e:
                    logger.error("MediaPlayer.%s() failed: %s", action, e)

            logger.info("[MusicPlayer] Music %s (no player available).", action)
            return SkillResult(
                spoken_response=f"I have {action}d the music.", success=True
            )

        # --- NEXT ---
        if action == "next":
            if media_player:
                try:
                    await media_player.next()
                    logger.info("[MusicPlayer] Skipped to next track.")
                    return SkillResult(
                        spoken_response="Skipping to the next track.",
                        success=True,
                    )
                except Exception as e:
                    logger.error("MediaPlayer.next() failed: %s", e)

            logger.info("[MusicPlayer] Skip requested (no player available).")
            return SkillResult(
                spoken_response="Skipping to the next track.", success=True
            )

        return SkillResult(
            spoken_response="I'm not sure how to control the music.",
            success=False,
        )

    @staticmethod
    def _browser_play(song: str) -> SkillResult:
        """Fallback: open YouTube in browser."""
        if song:
            query = urllib.parse.quote(f"{song} song")
            display = song
        else:
            query = urllib.parse.quote("trending music")
            display = "some music"

        url = f"https://www.youtube.com/results?search_query={query}"
        try:
            webbrowser.open(url)
            logger.info("[MusicPlayer] Browser fallback: %s", url)
        except Exception as e:
            logger.error("Failed to open browser: %s", e)

        return SkillResult(
            spoken_response=f"Playing {display}.",
            success=True,
            memory_item=f"Music playing: {display}",
        )
