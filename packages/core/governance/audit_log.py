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
    """Append-only JSON-lines and SQL database audit log."""

    def __init__(
        self,
        log_path: str = "data/audit.jsonl",
        *,
        persistence: Optional[PersistenceContext] = None,
    ) -> None:
        from packages.core.memory.persistence import PersistenceContext

        self._path = Path(log_path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self.persistence = persistence

    def record(
        self,
        *,
        event: str,
        user_id: str = "unknown",
        user_role: str = "guest",
        details: Optional[dict] = None,
        allowed: Optional[bool] = None,
    ) -> None:
        """Append an audit entry to the JSONL file and database."""
        entry = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "event": event,
            "user_id": user_id,
            "user_role": user_role,
            "allowed": allowed,
            "details": details or {},
        }
        line = json.dumps(entry, ensure_ascii=False)

        # 1. Write to plain-text backup
        try:
            with open(self._path, "a", encoding="utf-8") as f:
                f.write(line + "\n")
        except OSError as exc:
            logger.error("Failed to write audit log file: %s", exc)

        # 2. Write to unified SQL database
        if self.persistence:
            try:
                import uuid

                log_id = str(uuid.uuid4())
                allowed_int = (
                    1 if allowed is True else (0 if allowed is False else None)
                )
                details_json = json.dumps(details) if details else None

                with self.persistence.get_connection() as conn:
                    conn.execute(
                        """
                        INSERT INTO audit_logs (id, ts, event, user_id, user_role, allowed, details)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            log_id,
                            entry["ts"],
                            event,
                            user_id,
                            user_role,
                            allowed_int,
                            details_json,
                        ),
                    )
                    conn.commit()
            except Exception as exc:
                logger.error("Failed to write audit log to database: %s", exc)

    def read_recent(self, n: int = 50) -> list[dict]:
        """Read the last *n* entries (most-recent-last)."""
        # If database persistence is active, retrieve from SQL
        if self.persistence:
            try:
                with self.persistence.get_connection() as conn:
                    rows = conn.execute(
                        """
                        SELECT ts, event, user_id, user_role, allowed, details 
                        FROM audit_logs 
                        ORDER BY ts DESC 
                        LIMIT ?
                        """,
                        (n,),
                    ).fetchall()
                results = []
                for ts, event, user_id, user_role, allowed_val, details_json in reversed(
                    rows
                ):
                    allowed = (
                        True
                        if allowed_val == 1
                        else (False if allowed_val == 0 else None)
                    )
                    results.append(
                        {
                            "ts": ts,
                            "event": event,
                            "user_id": user_id,
                            "user_role": user_role,
                            "allowed": allowed,
                            "details": (
                                json.loads(details_json) if details_json else {}
                            ),
                        }
                    )
                return results
            except Exception as exc:
                logger.error("Failed to read audit log from database: %s", exc)

        # Fallback to JSONL file reading
        if not self._path.exists():
            return []
        try:
            lines = self._path.read_text(encoding="utf-8").strip().splitlines()
            recent = lines[-n:] if len(lines) > n else lines
            return [json.loads(line) for line in recent]
        except Exception as exc:
            logger.error("Failed to read audit log: %s", exc)
            return []
