"""
Real Home automation port adapter routing commands to MQTT, Kasa, or Broadlink devices.
"""

import logging
from typing import Any, Dict, Optional

from packages.core.config import AppConfig
from packages.core.home.mqtt_client import MqttHomeClient
from packages.core.ports.home import HomePort

try:
    import kasa
except ImportError:
    kasa = None

try:
    import broadlink
except ImportError:
    broadlink = None

logger = logging.getLogger(__name__)


class RealHomeAdapter(HomePort):
    """
    Smart home adapter implementing HomePort.
    Routes calls to physical devices based on configuration.
    """

    def __init__(
        self, config: AppConfig, mqtt_client: Optional[MqttHomeClient] = None
    ) -> None:
        self.config = config
        self.mqtt_client = mqtt_client
        self.mock_states: Dict[str, Dict[str, Any]] = {}

    async def set_switch(self, device_id: str, on: bool) -> bool:
        """Set binary switch (on/off) state for a device."""
        device = self.config.home_devices.get(device_id)

        # 1. Default to MQTT Tasmota if not configured
        if not device:
            logger.info(
                f"Device '{device_id}' not configured, "
                "defaulting to Tasmota MQTT command."
            )
            if self.mqtt_client:
                topic = f"cmnd/{device_id}/POWER"
                payload = "ON" if on else "OFF"
                return await self.mqtt_client.publish(topic, payload)
            return False

        # 2. Configured routing
        if device.type == "mock":
            logger.info(f"[Mock Home] Device '{device_id}' set switch: {on}")
            self.mock_states[device_id] = {"on": on}
            return True

        elif device.type == "tasmota":
            if self.mqtt_client:
                topic = f"cmnd/{device.address}/POWER"
                payload = "ON" if on else "OFF"
                return await self.mqtt_client.publish(topic, payload)
            logger.warning("MQTT client not initialized; cannot control Tasmota.")
            return False

        elif device.type == "kasa":
            if kasa is None:
                logger.error(
                    "python-kasa is not installed; cannot control Kasa device."
                )
                return False
            try:
                plug = kasa.SmartPlug(device.address)
                await plug.update()
                if on:
                    await plug.turn_on()
                else:
                    await plug.turn_off()
                logger.info(f"Kasa device '{device_id}' turned {'on' if on else 'off'}")
                return True
            except Exception as e:
                logger.error(f"Failed to control Kasa device at {device.address}: {e}")
                return False

        elif device.type == "broadlink":
            # IR power toggles / commands
            cmd_name = "ON" if on else "OFF"
            if device.ir_commands and cmd_name in device.ir_commands:
                return await self.send_ir(device_id, cmd_name)
            logger.warning(
                f"Broadlink device '{device_id}' lacks '{cmd_name}' IR command mapping."
            )
            return False

        logger.error(
            f"Unsupported device type: '{device.type}' for device '{device_id}'"
        )
        return False

    async def set_level(self, device_id: str, pct: int) -> bool:
        """Set brightness or level (0-100) for a device."""
        device = self.config.home_devices.get(device_id)

        if not device:
            if self.mqtt_client:
                topic = f"cmnd/{device_id}/Dimmer"
                payload = str(pct)
                return await self.mqtt_client.publish(topic, payload)
            return False

        if device.type == "mock":
            logger.info(f"[Mock Home] Device '{device_id}' set level: {pct}%")
            self.mock_states[device_id] = {"pct": pct}
            return True

        elif device.type == "tasmota":
            if self.mqtt_client:
                topic = f"cmnd/{device.address}/Dimmer"
                payload = str(pct)
                return await self.mqtt_client.publish(topic, payload)
            return False

        elif device.type == "kasa":
            if kasa is None:
                logger.error(
                    "python-kasa is not installed; cannot control Kasa device."
                )
                return False
            try:
                # Dimmers or bulbs use SmartBulb or SmartDimmer
                bulb = kasa.SmartBulb(device.address)
                await bulb.update()
                await bulb.set_brightness(pct)
                logger.info(f"Kasa bulb '{device_id}' brightness set to {pct}%")
                return True
            except Exception as e:
                logger.error(f"Failed to set Kasa brightness at {device.address}: {e}")
                return False

        logger.error(f"Device type '{device.type}' does not support setting level.")
        return False

    async def send_ir(self, device_id: str, command: str) -> bool:
        """Send IR command bytes via Broadlink RM."""
        device = self.config.home_devices.get(device_id)
        if not device:
            logger.warning(f"Device '{device_id}' not configured; cannot send IR.")
            return False

        if device.type == "mock":
            logger.info(f"[Mock Home] Device '{device_id}' sent IR command: {command}")
            return True

        if device.type == "broadlink":
            if broadlink is None:
                logger.error("broadlink library is not installed.")
                return False

            if not device.ir_commands or command not in device.ir_commands:
                logger.error(
                    f"No IR code mapped for command '{command}' on device '{device_id}'"
                )
                return False

            hex_code = device.ir_commands[command]
            try:
                # Convert hex command representation back into bytes
                packet = bytes.fromhex(hex_code)
                dev = broadlink.hello(device.address)
                dev.auth()
                dev.send_data(packet)
                logger.info(
                    f"Broadlink RM sent IR command '{command}' to device '{device_id}'"
                )
                return True
            except Exception as e:
                logger.error(
                    f"Failed to transmit IR via Broadlink RM at {device.address}: {e}"
                )
                return False

        logger.error(f"Device '{device_id}' is not an IR/Broadlink device.")
        return False

    async def get_state(self, device_id: str) -> Dict[str, Any]:
        """Query current state parameters for a device."""
        device = self.config.home_devices.get(device_id)

        if not device or device.type == "mock":
            return self.mock_states.get(device_id, {})

        if device.type == "tasmota":
            if self.mqtt_client:
                val = self.mqtt_client.states.get(device.address, "")
                return {"on": val.upper() == "ON"}
            return {}

        elif device.type == "kasa":
            if kasa is None:
                return {}
            try:
                plug = kasa.SmartPlug(device.address)
                await plug.update()
                return {"on": plug.is_on}
            except Exception:
                return {}

        return {}
