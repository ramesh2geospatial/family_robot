"""
Desktop mock/logging home automation adapter.
"""

import logging
from typing import Any, Dict

from packages.core.ports.home import HomePort

logger = logging.getLogger(__name__)


class DesktopHomeAdapter(HomePort):
    def __init__(self) -> None:
        self.states: Dict[str, Any] = {}

    async def set_switch(self, device_id: str, on: bool) -> bool:
        """Set a binary switch (on/off) for a device."""
        logger.info("DesktopHomeAdapter: set_switch %s -> %s", device_id, on)
        self.states[device_id] = {"on": on}
        return True

    async def set_level(self, device_id: str, pct: int) -> bool:
        """Set level (brightness/speed pct) for a device."""
        logger.info("DesktopHomeAdapter: set_level %s -> %d%%", device_id, pct)
        self.states[device_id] = {"pct": pct}
        return True

    async def send_ir(self, device_id: str, command: str) -> bool:
        """Send an infrared command to a device."""
        logger.info("DesktopHomeAdapter: send_ir to %s command %s", device_id, command)
        return True

    async def get_state(self, device_id: str) -> Dict[str, Any]:
        """Get the current state dictionary of a device."""
        state = self.states.get(device_id, {})
        logger.info("DesktopHomeAdapter: get_state for %s -> %s", device_id, state)
        return state
