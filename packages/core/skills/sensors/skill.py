import logging
import json
import asyncio
from packages.core.skills.base import BaseSkill, SkillContext, SkillResult

logger = logging.getLogger(__name__)

class SensorsSkill(BaseSkill):
    """
    Skill to check door and smoke sensor statuses, and react to Zigbee2MQTT changes.
    """

    def __init__(self) -> None:
        self.door_open = False
        self.smoke_detected = False

    @property
    def name(self) -> str:
        return "sensors"

    @property
    def required_permissions(self) -> list[str]:
        return ["general_info"]

    def handle_mqtt_message(self, topic: str, payload: str, ports: dict) -> None:
        """
        Handle incoming MQTT sensor state updates from Zigbee2MQTT.
        """
        logger.info(f"[Sensors MQTT] Topic={topic} Payload={payload}")
        try:
            data = json.loads(payload)
            # Match front door contact sensor
            if "front_door" in topic:
                # contact = True means closed, contact = False means open
                self.door_open = not data.get("contact", True)
                if self.door_open:
                    logger.warning("Front door is open!")

            # Match kitchen smoke sensor
            elif "kitchen_smoke" in topic:
                self.smoke_detected = data.get("smoke", False)
                if self.smoke_detected:
                    logger.critical("KITCHEN SMOKE ALARM DETECTED!")
                    notify = ports.get("notify")
                    if notify:
                        # Push critical warning
                        asyncio.create_task(notify.push(
                            user_id="parent_default",
                            title="FIRE ALERT",
                            body="Kitchen smoke sensor has triggered!"
                        ))
        except Exception as e:
            logger.error(f"Failed to process sensor MQTT update: {e}")

    async def execute(self, ctx: SkillContext) -> SkillResult:
        status_msg = "Front door is open." if self.door_open else "Front door is closed."
        if self.smoke_detected:
            status_msg += " Warning: Smoke detected in kitchen!"
        else:
            status_msg += " Smoke detectors are clear."

        return SkillResult(
            spoken_response=status_msg,
            success=True
        )
