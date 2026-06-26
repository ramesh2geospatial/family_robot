"""
Abstract home automation port interface.
"""

from typing import Any, Dict, Protocol, runtime_checkable


@runtime_checkable
class HomePort(Protocol):
    async def set_switch(self, device_id: str, on: bool) -> bool:
        """Set a binary switch (on/off) for a device."""
        ...

    async def set_level(self, device_id: str, pct: int) -> bool:
        """Set level (brightness/speed pct) for a device."""
        ...

    async def send_ir(self, device_id: str, command: str) -> bool:
        """Send an infrared command to a device."""
        ...

    async def get_state(self, device_id: str) -> Dict[str, Any]:
        """Get the current state dictionary of a device."""
        ...
