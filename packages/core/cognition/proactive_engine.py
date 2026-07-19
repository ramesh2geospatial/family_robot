"""
Proactive intelligence engine for FamilyRobot.

Periodically evaluates family patterns and generates proactive
suggestions based on time, device state, and learned memories.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Optional

logger = logging.getLogger(__name__)

# Quiet hours: don't proactively speak during these times
_QUIET_START = 22  # 10 PM
_QUIET_END = 6  # 6 AM

# Minimum interval between proactive suggestions (seconds)
_MIN_INTERVAL_S = 300  # 5 minutes


class ProactiveEngine:
    """Background engine that generates proactive suggestions.

    Called periodically by the main loop during idle cycles. Returns
    a suggestion string to speak, or None if there's nothing to say.
    """

    def __init__(self, *, quiet_start: int = _QUIET_START, quiet_end: int = _QUIET_END) -> None:
        self._quiet_start = quiet_start
        self._quiet_end = quiet_end
        self._last_suggestion_time: float = 0
        self._greeted_users: set[str] = set()  # Track who's been greeted today
        self._last_greeting_date: Optional[str] = None

    async def check(
        self,
        *,
        memory_port: Any = None,
        home_port: Any = None,
        current_user: Optional[str] = None,
        active_state: Optional[dict] = None,
    ) -> Optional[str]:
        """Evaluate context and return a proactive suggestion, or None.

        Args:
            memory_port: MemoryStore for looking up learned facts.
            home_port: HomePort for checking device states.
            current_user: Name of the last identified user (if any).
            active_state: Current robot state dict (media, timers, etc.).

        Returns:
            A spoken suggestion string, or None.
        """
        import time

        now = datetime.now()

        # Respect quiet hours
        if self._is_quiet_hours(now):
            return None

        # Rate-limit suggestions
        elapsed = time.monotonic() - self._last_suggestion_time
        if elapsed < _MIN_INTERVAL_S and self._last_suggestion_time > 0:
            return None

        suggestion = None

        # Reset daily greeting tracker
        today = now.strftime("%Y-%m-%d")
        if self._last_greeting_date != today:
            self._greeted_users.clear()
            self._last_greeting_date = today

        # ── Time-based triggers ──

        # Morning greeting (6-9 AM, once per user per day)
        if 6 <= now.hour < 9 and current_user:
            if current_user not in self._greeted_users:
                self._greeted_users.add(current_user)
                suggestion = await self._morning_greeting(
                    current_user, now, memory_port
                )

        # Late night reminder (after 10 PM)
        if now.hour >= 22 and current_user:
            suggestion = suggestion or self._late_night_reminder(current_user, now)

        # ── State-based triggers ──

        # Check for devices that should be warned about
        if home_port and not suggestion:
            suggestion = await self._check_device_warnings(home_port)

        if suggestion:
            self._last_suggestion_time = time.monotonic()

        return suggestion

    def _is_quiet_hours(self, now: datetime) -> bool:
        """Return True if it's quiet hours (no proactive speaking)."""
        hour = now.hour
        if self._quiet_start > self._quiet_end:
            # Wraps midnight: e.g., 22-6
            return hour >= self._quiet_start or hour < self._quiet_end
        return self._quiet_start <= hour < self._quiet_end

    async def _morning_greeting(
        self, user_name: str, now: datetime, memory_port: Any
    ) -> str:
        """Generate a personalized morning greeting."""
        greeting = f"Good morning, {user_name}!"

        # Try to add a personalized touch from memories
        if memory_port:
            try:
                hits = await memory_port.search(
                    f"{user_name} morning routine schedule", k=2
                )
                relevant = [
                    h["text"]
                    for h in hits
                    if h.get("score", 0.0) >= 0.55
                ]
                if relevant:
                    # Add the most relevant reminder
                    greeting += f" Just a reminder: {relevant[0]}"
            except Exception:
                pass

        return greeting

    def _late_night_reminder(self, user_name: str, now: datetime) -> str:
        """Gentle bedtime suggestion."""
        return (
            f"It's getting late, {user_name}. "
            "Should I turn off the lights and set an alarm for tomorrow?"
        )

    async def _check_device_warnings(self, home_port: Any) -> Optional[str]:
        """Check if any devices need attention."""
        # Check geyser state (common safety concern)
        try:
            state = await home_port.get_state("geyser")
            if state.get("on", False):
                return (
                    "Just a heads up — the geyser is still on. "
                    "Should I turn it off?"
                )
        except Exception:
            pass

        return None
