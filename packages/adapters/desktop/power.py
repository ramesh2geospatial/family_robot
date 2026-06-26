"""
Desktop power adapter (mains-only).
"""

from typing import Any, Callable, Optional

from packages.core.ports.power import PowerPort


class DesktopPowerAdapter(PowerPort):
    async def battery_pct(self) -> Optional[int]:
        """Return the current battery percentage, or None if mains-only."""
        return None

    async def on_low_power(self, cb: Callable[[], Any]) -> None:
        """Register a callback to trigger on low power events (safe shutdown)."""
        # No battery on desktop, so this is a no-op
        pass
