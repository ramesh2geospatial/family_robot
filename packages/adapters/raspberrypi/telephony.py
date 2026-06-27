"""
Telephony adapter for Raspberry Pi.
Relays call commands to Android satellites via MQTT.
"""

import json
import logging

from packages.core.home.mqtt_client import MqttHomeClient
from packages.core.ports.telephony import TelephonyPort

logger = logging.getLogger(__name__)


class PiTelephonyAdapter(TelephonyPort):
    """
    Raspberry Pi telephony adapter republishing to MQTT topics.
    """

    def __init__(self, mqtt_client: MqttHomeClient = None) -> None:
        self.mqtt = mqtt_client

    async def make_call(self, phone_number: str) -> bool:
        if self.mqtt and self.mqtt.is_connected:
            logger.info(
                f"Relaying call command to Android satellite via MQTT: {phone_number}"
            )
            return await self.mqtt.publish(
                "familyrobot/android/telephony/call", phone_number
            )
        logger.info(f"[Telephony Mock] Pi voice call to {phone_number}")
        return True

    async def open_whatsapp(self, phone_number: str, message: str) -> bool:
        if self.mqtt and self.mqtt.is_connected:
            payload = json.dumps({"number": phone_number, "message": message})
            logger.info(
                f"Relaying WhatsApp command to Android satellite via MQTT: {phone_number}"
            )
            return await self.mqtt.publish(
                "familyrobot/android/telephony/whatsapp", payload
            )
        logger.info(f"[Telephony Mock] Pi WhatsApp message to {phone_number}")
        return True
