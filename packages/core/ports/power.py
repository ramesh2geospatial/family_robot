"""
Abstract power/battery monitoring port interface.
"""

from typing import Any, Callable, Optional, Protocol, runtime_checkable


@runtime_checkable
class PowerPort(Protocol):
    async def battery_pct(self) -> Optional[int]:
        """Return the current battery percentage, or None if mains-only."""
        ...

    async def on_low_power(self, cb: Callable[[], Any]) -> None:
        """Register a callback to trigger on low power events (safe shutdown)."""
        ...
