"""
Media player for FamilyRobot.

Uses yt-dlp to resolve YouTube audio URLs and mpv for headless playback
with IPC-based transport controls (pause/resume/stop/next).

Falls back to opening a browser if mpv or yt-dlp are unavailable.
"""

from __future__ import annotations

import json
import logging
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import urllib.parse
import webbrowser
from typing import Optional

logger = logging.getLogger(__name__)

# IPC socket/pipe path
_IPC_PATH = os.path.join(tempfile.gettempdir(), "familyrobot_mpv_ipc")
if sys.platform == "win32":
    _IPC_PATH = r"\\.\pipe\familyrobot_mpv_ipc"


def _get_mpv_path() -> Optional[str]:
    """Find the path to the mpv executable, including winget local packages."""
    path_check = shutil.which("mpv")
    if path_check:
        return path_check

    # Fallback to local winget package path on Windows
    if sys.platform == "win32":
        local_app_data = os.environ.get("LOCALAPPDATA")
        if local_app_data:
            packages_dir = os.path.join(local_app_data, "Microsoft", "WinGet", "Packages")
            if os.path.exists(packages_dir):
                try:
                    for folder in os.listdir(packages_dir):
                        if folder.startswith("mpv-player.mpv-CI.MSVC"):
                            exe_path = os.path.join(packages_dir, folder, "mpv.exe")
                            if os.path.exists(exe_path):
                                return exe_path
                except Exception:
                    pass
    return None


def _ytdlp_available() -> bool:
    """Check if yt-dlp Python module is importable."""
    try:
        import yt_dlp  # noqa: F401

        return True
    except ImportError:
        return False


class MediaPlayer:
    """Headless media player using yt-dlp + mpv.

    Provides play/pause/resume/stop/next with graceful fallback to
    ``webbrowser.open()`` when mpv is not installed.
    """

    def __init__(self) -> None:
        self._mpv_path = _get_mpv_path()
        self._mpv_available = self._mpv_path is not None
        self._ytdlp_available = _ytdlp_available()
        self._process: Optional[subprocess.Popen] = None
        self._current_title: str = ""
        self._lock = threading.Lock()
        self._is_ducked: bool = False
        self._original_volume: int = 100

        if not self._mpv_available:
            logger.warning(
                "mpv not found on PATH. Music will open in browser instead. "
                "Install mpv for inline playback: https://mpv.io"
            )
        if not self._ytdlp_available:
            logger.warning(
                "yt-dlp not installed. Install with: pip install yt-dlp"
            )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def can_play_inline(self) -> bool:
        """True if we can play audio without opening a browser."""
        return self._mpv_available and self._ytdlp_available

    @property
    def current_title(self) -> str:
        return self._current_title

    def is_playing(self) -> bool:
        with self._lock:
            return self._process is not None and self._process.poll() is None

    async def play(self, query: str) -> str:
        """Search YouTube for *query* and play the first result.

        Returns the title of the song being played.
        Falls back to browser if mpv/yt-dlp unavailable.
        """
        if not query:
            query = "trending Hindi songs"

        if not self.can_play_inline:
            return self._browser_fallback(query)

        # Stop any current playback first
        await self.stop()

        # Resolve via yt-dlp
        title, audio_url = await self._resolve_url(query)
        if not audio_url:
            return self._browser_fallback(query)

        # Launch mpv in headless mode
        self._start_mpv(audio_url, title)
        return title

    async def pause(self) -> bool:
        """Toggle pause on current playback."""
        # Cancel any active unduck tasks and reset ducked state
        if hasattr(self, "_unduck_task") and self._unduck_task:
            self._unduck_task.cancel()
            self._unduck_task = None
        self._is_ducked = False
        return self._send_ipc_command({"command": ["cycle", "pause"]})

    async def resume(self) -> bool:
        """Resume playback (alias for pause toggle)."""
        return self._send_ipc_command(
            {"command": ["set_property", "pause", False]}
        )

    async def stop(self) -> None:
        """Stop playback and kill mpv process."""
        if hasattr(self, "_unduck_task") and self._unduck_task:
            self._unduck_task.cancel()
            self._unduck_task = None
        self._is_ducked = False

        with self._lock:
            if self._process and self._process.poll() is None:
                try:
                    self._process.terminate()
                    self._process.wait(timeout=3)
                except Exception:
                    try:
                        self._process.kill()
                    except Exception:
                        pass
                logger.info("Playback stopped.")
            self._process = None
            self._current_title = ""

    async def next(self) -> str:
        """Skip to next (plays a related search). Returns new title."""
        # mpv single-file mode doesn't have a playlist, so we just stop
        # In a future version, we could maintain a playlist
        await self.stop()
        return ""

    async def set_volume(self, pct: int) -> bool:
        """Set playback volume (0-100) via IPC."""
        logger.info("Setting volume to %d%%", pct)
        return self._send_ipc_command(
            {"command": ["set_property", "volume", pct]}
        )

    async def duck(self, pct: int = 50, duration: float = 3.0) -> None:
        """Temporarily lower the volume (duck) and schedule auto-unduck."""
        if not self.is_playing():
            return

        # Cancel any active auto-unduck task
        if hasattr(self, "_unduck_task") and self._unduck_task:
            self._unduck_task.cancel()
            self._unduck_task = None

        if not self._is_ducked:
            logger.info("Ducking playback volume to %d%%", pct)
            self._is_ducked = True
            await self.set_volume(pct)

        # Spawn self-unducking background task
        import asyncio
        self._unduck_task = asyncio.create_task(self._auto_unduck_delay(duration))

    async def _auto_unduck_delay(self, duration: float) -> None:
        import asyncio
        try:
            await asyncio.sleep(duration)
            await self.unduck()
        except asyncio.CancelledError:
            pass

    async def unduck(self) -> None:
        """Restore the volume to original level."""
        if not self.is_playing() or not self._is_ducked:
            return
        logger.info("Restoring playback volume to %d%%", self._original_volume)
        self._is_ducked = False
        await self.set_volume(self._original_volume)



    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    async def _resolve_url(self, query: str) -> tuple[str, str]:
        """Use yt-dlp to search YouTube and extract audio URL.

        Returns (title, audio_url) or ("", "") on failure.
        """
        import asyncio

        try:
            return await asyncio.to_thread(self._resolve_url_sync, query)
        except Exception as exc:
            logger.error("yt-dlp resolution failed: %s", exc)
            return ("", "")

    def _resolve_url_sync(self, query: str) -> tuple[str, str]:
        """Synchronous yt-dlp resolution."""
        try:
            import yt_dlp
        except ImportError:
            return ("", "")

        ydl_opts = {
            "format": "bestaudio/best",
            "quiet": True,
            "no_warnings": True,
            "extract_flat": False,
            "noplaylist": True,
            "default_search": "ytsearch1",
            # Don't download, just extract info
            "skip_download": True,
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(query, download=False)

                if not info:
                    return ("", "")

                # ytsearch returns entries list
                if "entries" in info and info["entries"]:
                    entry = info["entries"][0]
                else:
                    entry = info

                title = entry.get("title", query)
                url = entry.get("url", "")

                # If url is empty, try webpage_url for mpv to handle
                if not url:
                    url = entry.get("webpage_url", "")

                logger.info("Resolved: '%s' → '%s'", query, title)
                return (title, url)
        except Exception as exc:
            logger.error("yt-dlp extraction error: %s", exc)
            return ("", "")

    def _start_mpv(self, url: str, title: str) -> None:
        """Launch mpv in headless audio-only mode."""
        mpv_bin = self._mpv_path or "mpv"
        cmd = [
            mpv_bin,
            "--no-video",
            "--really-quiet",
            "--no-terminal",
            f"--input-ipc-server={_IPC_PATH}",
            f"--title={title}",
            url,
        ]

        with self._lock:
            try:
                # Use CREATE_NO_WINDOW on Windows to avoid cmd popup
                kwargs = {}
                if sys.platform == "win32":
                    kwargs["creationflags"] = (
                        subprocess.CREATE_NO_WINDOW  # type: ignore[attr-defined]
                    )

                self._process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    **kwargs,
                )
                self._current_title = title
                logger.info(
                    "mpv started (PID %d): %s", self._process.pid, title
                )
            except FileNotFoundError:
                logger.error("mpv binary not found despite earlier check.")
                self._process = None
            except Exception as exc:
                logger.error("Failed to start mpv: %s", exc)
                self._process = None

    def _send_ipc_command(self, cmd: dict) -> bool:
        """Send a JSON IPC command to mpv."""
        if not self.is_playing():
            return False

        payload = json.dumps(cmd) + "\n"

        try:
            if sys.platform == "win32":
                return self._send_ipc_windows(payload)
            else:
                return self._send_ipc_unix(payload)
        except Exception as exc:
            logger.warning("IPC command failed: %s", exc)
            return False

    def _send_ipc_unix(self, payload: str) -> bool:
        """Send IPC via Unix domain socket."""
        import socket

        try:
            sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            sock.connect(_IPC_PATH)
            sock.sendall(payload.encode())
            sock.close()
            return True
        except Exception as exc:
            logger.warning("Unix IPC failed: %s", exc)
            return False

    def _send_ipc_windows(self, payload: str) -> bool:
        """Send IPC via Windows named pipe."""
        try:
            with open(_IPC_PATH, "w") as pipe:
                pipe.write(payload)
            return True
        except FileNotFoundError:
            # Pipe not ready yet
            logger.debug("Named pipe not ready: %s", _IPC_PATH)
            return False
        except Exception as exc:
            logger.warning("Windows IPC failed: %s", exc)
            return False

    def _browser_fallback(self, query: str) -> str:
        """Open YouTube search in browser as fallback."""
        encoded = urllib.parse.quote(f"{query} song")
        url = f"https://www.youtube.com/results?search_query={encoded}"
        try:
            webbrowser.open(url)
            logger.info("Browser fallback: opened YouTube search for '%s'", query)
        except Exception as exc:
            logger.error("Browser fallback failed: %s", exc)
        return f"{query} (opened in browser)"
