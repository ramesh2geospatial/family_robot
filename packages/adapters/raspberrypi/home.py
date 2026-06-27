"""
Raspberry Pi home adapter extending RealHomeAdapter with lgpio relay support.
"""

import logging
from typing import Any, Optional

from packages.core.config import AppConfig
from packages.core.home.adapter import RealHomeAdapter
from packages.core.home.mqtt_client import MqttHomeClient

logger = logging.getLogger(__name__)


class PiHomeAdapter(RealHomeAdapter):
    """
    Smart home adapter for Raspberry Pi.
    Overrides set_switch to directly control GPIO pins if device.type == "gpio".
    Otherwise, delegates to RealHomeAdapter for network smart-home.
    """

    def __init__(
        self, config: AppConfig, mqtt_client: Optional[MqttHomeClient] = None
    ) -> None:
        super().__init__(config, mqtt_client)
        self._chip_handle: Any = None
        self._claimed_pins = set()

    @property
    def _lgpio(self) -> Any:
        try:
            import lgpio

            return lgpio
        except ImportError:
            return None

    def _open_chip(self) -> Any:
        lib = self._lgpio
        if lib is None:
            return None
        # Chip 4 is standard for RP1 GPIO header on Pi 5; Chip 0 is Pi 4.
        for chip in [4, 0]:
            try:
                handle = lib.gpiochip_open(chip)
                logger.info(f"Opened lgpio chip {chip} successfully.")
                return handle
            except Exception:
                pass
        return None

    async def set_switch(self, device_id: str, on: bool) -> bool:
        """Set switch state, intercepting 'gpio' device types for physical relays."""
        device = self.config.home_devices.get(device_id)
        if device and device.type == "gpio":
            lib = self._lgpio
            if lib is None:
                logger.warning(
                    f"lgpio library not installed; logging mock "
                    f"GPIO pin {device.address} to {on}."
                )
                self.mock_states[device_id] = {"on": on}
                return True
            try:
                pin = int(device.address)
                if self._chip_handle is None:
                    self._chip_handle = self._open_chip()
                    if self._chip_handle is None:
                        raise RuntimeError("Failed to open any lgpio chip.")
                if pin not in self._claimed_pins:
                    lib.gpio_claim_output(self._chip_handle, pin)
                    self._claimed_pins.add(pin)
                lib.gpio_write(self._chip_handle, pin, 1 if on else 0)
                logger.info(
                    f"Pi GPIO pin {pin} written: {1 if on else 0} "
                    f"for device '{device_id}'"
                )
                self.mock_states[device_id] = {"on": on}
                return True
            except Exception as e:
                logger.error(
                    f"Failed to control Pi GPIO pin for device '{device_id}': {e}"
                )
                return False

        return await super().set_switch(device_id, on)

    async def close(self) -> None:
        """Release GPIO chip handle on shutdown."""
        lib = self._lgpio
        if lib and self._chip_handle is not None:
            try:
                lib.gpiochip_close(self._chip_handle)
            except Exception as e:
                logger.warning(f"Error closing lgpio chip: {e}")
            self._chip_handle = None
            self._claimed_pins.clear()
            logger.info("Pi GPIO chip closed.")
