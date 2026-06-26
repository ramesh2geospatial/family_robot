"""
Termux power/battery status adapter for Android.
Fetches system battery percentage via termux-battery-status JSON.
"""

import asyncio
import json
import logging
import shutil
import subprocess
from typing import Any, Callable, Optional

from packages.core.ports.power import PowerPort

logger = logging.getLogger(__name__)


class TermuxPowerAdapter(PowerPort):
    """
    Battery status adapter for Android Termux.
    Queries the Termux API to find battery percentage and charging status.
    """

    def __init__(self) -> None:
        self._callback: Optional[Callable[[], Any]] = None
        self._monitor_task: Optional[asyncio.Task] = None

    async def battery_pct(self) -> Optional[int]:
        """Return current battery percentage, or 100 as fallback."""
        if not shutil.which("termux-battery-status"):
            # Return mock battery level if run in non-Android environment
            return 100
        try:
            res = await asyncio.to_thread(
                subprocess.run,
                ["termux-battery-status"],
                capture_output=True,
                text=True,
                check=True,
            )
            data = json.loads(res.stdout)
            return data.get("percentage")
        except Exception as e:
            logger.error(f"Failed to query termux-battery-status: {e}")
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
                    if not shutil.which("termux-battery-status"):
                        continue
                    res = await asyncio.to_thread(
                        subprocess.run,
                        ["termux-battery-status"],
                        capture_output=True,
                        text=True,
                        check=True,
                    )
                    data = json.loads(res.stdout)
                    pct = data.get("percentage")
                    status = data.get("status")

                    # Trigger if battery drops below 15% and is actively discharging
                    if pct is not None and pct < 15 and status == "DISCHARGING":
                        logger.warning(
                            f"Low battery alert ({pct}%). Activating callback."
                        )
                        if asyncio.iscoroutinefunction(self._callback):
                            await self._callback()
                        else:
                            self._callback()
                except Exception as e:
                    logger.error(f"Error in battery monitor loop: {e}")
