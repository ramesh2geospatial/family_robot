"""
Append-only conversation log for FamilyRobot.

Records user queries, transcribed text, intent routing, and robot responses.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class ConversationLogger:
    """Logs conversation exchanges for diagnostic and learning purposes."""

    def __init__(self, log_path: str = "data/conversations.jsonl") -> None:
        self._path = Path(log_path)
        self._path.parent.mkdir(parents=True, exist_ok=True)

    def log_interaction(
        self,
        *,
        user_id: str = "unknown",
        user_role: str = "guest",
        audio_duration_s: float = 0.0,
        detected_language: str = "en",
        raw_text: str,
        intent: str = "unknown",
        intent_confidence: float = 0.0,
        response_text: str,
        processing_time_s: float = 0.0,
        tts_engine: str = "pyttsx3",
    ) -> None:
        """Appends a new interaction record to the conversation log."""
        entry = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "user_id": user_id,
            "user_role": user_role,
            "audio_duration_s": round(audio_duration_s, 2),
            "detected_language": detected_language,
            "input_text": raw_text,
            "intent": intent,
            "intent_confidence": round(intent_confidence, 2),
            "response_text": response_text,
            "processing_time_s": round(processing_time_s, 3),
            "tts_engine": tts_engine,
        }
        line = json.dumps(entry, ensure_ascii=False)
        try:
            with open(self._path, "a", encoding="utf-8") as f:
                f.write(line + "\n")
        except OSError as exc:
            logger.error("Failed to write conversation log: %s", exc)

    def get_recent(self, n: int = 50) -> list[dict]:
        """Read recent conversation entries (most-recent-last)."""
        if not self._path.exists():
            return []
        try:
            lines = self._path.read_text(encoding="utf-8").strip().splitlines()
            recent = lines[-n:] if len(lines) > n else lines
            return [json.loads(line) for line in recent if line.strip()]
        except Exception as exc:
            logger.error("Failed to read conversation log: %s", exc)
            return []
