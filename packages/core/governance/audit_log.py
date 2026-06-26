"""
Append-only audit log for FamilyRobot.

Records every significant action (ACL checks, device commands, memory
writes) as JSON-lines for accountability and debugging.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class AuditLog:
    """Append-only JSON-lines audit log."""

    def __init__(self, log_path: str = "data/audit.jsonl") -> None:
        self._path = Path(log_path)
        self._path.parent.mkdir(parents=True, exist_ok=True)

    def record(
        self,
        *,
        event: str,
        user_id: str = "unknown",
        user_role: str = "guest",
        details: Optional[dict] = None,
        allowed: Optional[bool] = None,
    ) -> None:
        """Append an audit entry.

        Parameters
        ----------
        event : str
            Short event identifier, e.g. ``"acl_check"``, ``"device_command"``.
        user_id : str
            Who triggered the action.
        user_role : str
            Role at the time of the action.
        details : dict, optional
            Arbitrary payload (intent, device, etc.).
        allowed : bool, optional
            Whether the action was permitted (for ACL events).
        """
        entry = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "event": event,
            "user_id": user_id,
            "user_role": user_role,
            "allowed": allowed,
            "details": details or {},
        }
        line = json.dumps(entry, ensure_ascii=False)

        try:
            with open(self._path, "a", encoding="utf-8") as f:
                f.write(line + "\n")
        except OSError as exc:
            logger.error("Failed to write audit log: %s", exc)

    def read_recent(self, n: int = 50) -> list[dict]:
        """Read the last *n* entries (most-recent-last)."""
        if not self._path.exists():
            return []
        try:
            lines = self._path.read_text(encoding="utf-8").strip().splitlines()
            recent = lines[-n:] if len(lines) > n else lines
            return [json.loads(line) for line in recent]
        except Exception as exc:
            logger.error("Failed to read audit log: %s", exc)
            return []
