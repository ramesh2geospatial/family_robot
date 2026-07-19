"""
Helper to read and write shared robot status.
Allows separate main loop and webapp processes to communicate active state.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

STATUS_FILE = Path("data/robot_status.json")

_last_written_data: dict = {}

def update_robot_status(
    status: str,
    current_song: Optional[str] = None,
    is_playing_music: Optional[bool] = None,
    last_speech_heard: Optional[str] = None,
    last_speech_spoken: Optional[str] = None,
) -> None:
    """Updates the shared robot status file with in-memory caching to prevent excessive IO."""
    global _last_written_data
    
    update = {"status": status}
    if current_song is not None:
        update["current_song"] = current_song
    if is_playing_music is not None:
        update["is_playing_music"] = is_playing_music
    if last_speech_heard is not None:
        update["last_speech_heard"] = last_speech_heard
    if last_speech_spoken is not None:
        update["last_speech_spoken"] = last_speech_spoken

    changed = False
    for k, v in update.items():
        if _last_written_data.get(k) != v:
            changed = True
            break

    if not changed and STATUS_FILE.exists():
        return

    try:
        STATUS_FILE.parent.mkdir(parents=True, exist_ok=True)
        
        data = {}
        if STATUS_FILE.exists():
            try:
                data = json.loads(STATUS_FILE.read_text(encoding="utf-8"))
            except Exception:
                pass

        data.update(update)
        STATUS_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        _last_written_data = data
    except Exception as exc:
        logger.warning("Failed to write shared robot status: %s", exc)

def read_robot_status() -> dict:
    """Reads the shared robot status file."""
    default = {
        "status": "idle",
        "current_song": "",
        "is_playing_music": False,
        "last_speech_heard": "",
        "last_speech_spoken": "",
    }
    if not STATUS_FILE.exists():
        return default
    try:
        data = json.loads(STATUS_FILE.read_text(encoding="utf-8"))
        for k, v in default.items():
            if k not in data:
                data[k] = v
        return data
    except Exception:
        return default
