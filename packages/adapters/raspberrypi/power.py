"""
Raspberry Pi battery power adapter using I2C SMBus interface.
Queries Waveshare / generic UPS HAT registers and monitors for low-power events.
"""

import asyncio
import logging
from typing import Any, Callable, Optional

from packages.core.ports.power import PowerPort

logger = logging.getLogger(__name__)


class PiPowerAdapter(PowerPort):
    """
    Power status adapter for Raspberry Pi.
    Reads battery capacity from I2C registers of standard UPS HATs.
    """

    def __init__(self) -> None:
        self._callback: Optional[Callable[[], Any]] = None
        self._monitor_task: Optional[asyncio.Task] = None

    @property
    def _smbus(self) -> Any:
        """Dynamically load smbus/smbus2 dependency to avoid module-level

        test import order conflicts.
        """
        try:
            import smbus2 as smbus

            return smbus
        except ImportError:
            try:
                import smbus

                return smbus
            except ImportError:
                return None

    async def battery_pct(self) -> Optional[int]:
        """Return the current battery percentage from I2C or 100 as fallback."""
        lib = self._smbus
        if lib is None:
            return 100

        # Try standard I2C addresses for Waveshare/generic Pi UPS HATs
        try:
            # Bus 1 is default on modern Pi
            bus = lib.SMBus(1)
            for addr in [0x42, 0x43]:
                try:
                    # Register 0x02 holds percentage on Waveshare boards
                    pct = bus.read_byte_data(addr, 0x02)
                    if 0 <= pct <= 100:
                        return pct
                except Exception:
                    pass
            # Default fallback if I2C query returns no matching board
            return 100
        except Exception as e:
            logger.debug(f"Pi I2C SMBus query failed: {e}")
            return 100

    async def on_low_power(self, cb: Callable[[], Any]) -> None:
        """Register a callback to run when battery levels run low (< 15%)."""
        self._callback = cb
        if self._monitor_task is None:
            self._monitor_task = asyncio.create_task(self._monitor_loop())

    async def _monitor_loop(self) -> None:
        """Background loop querying battery state every 60s."""
        while True:
            await asyncio.sleep(60)
            if self._callback:
                try:
                    pct = await self.battery_pct()
                    if pct is not None and pct < 15:
                        logger.warning(
                            f"Pi battery low ({pct}%). Executing low power callback."
                        )
                        if asyncio.iscoroutinefunction(self._callback):
                            await self._callback()
                        else:
                            self._callback()
                except Exception as e:
                    logger.error(f"Error in Pi battery monitor loop: {e}")
