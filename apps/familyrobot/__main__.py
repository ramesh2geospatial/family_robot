"""
Entrypoint for FamilyRobot.

    python -m apps.familyrobot [--platform desktop]

Loads config, wires all components, and runs the main voice loop.
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import signal
import sys

from apps.familyrobot.main_loop import run_loop
from apps.familyrobot.wiring import wire_components
from packages.core.cognition import IntentRouter, LlamaLLMClient
from packages.core.config import AppConfig, load_config
from packages.core.expression import PiperTTSEngine
from packages.core.governance import (
    ACL,
    AuditLog,
    ConversationLogger,
    FamilyMember,
    IdentityStore,
    Role,
)
from packages.core.memory import MemoryStore
from packages.core.perception import (
    SpeechToText,
    VoiceActivityDetector,
    WakeWordDetector,
)

logger = logging.getLogger(__name__)


def _build_components(config: AppConfig) -> dict:
    """Wire all components from *config* into a single dict."""
    mqtt_client = None
    if config.home_type == "real":
        from packages.core.home.mqtt_client import MqttHomeClient

        mqtt_client = MqttHomeClient(
            host=config.mqtt.host,
            port=config.mqtt.port,
            username=config.mqtt.username,
            password=config.mqtt.password,
            use_tls=config.mqtt.use_tls,
        )

    wired = wire_components(config, mqtt_client=mqtt_client)

    # Perception
    wakeword = WakeWordDetector(wake_word=config.system.wake_word)
    vad = VoiceActivityDetector()
    stt = SpeechToText()

    # Cognition
    llm = LlamaLLMClient(
        model_path=config.llm_model_path,
    )
    memory = MemoryStore(
        db_path=config.memory_db_path,
    )
    intent_router = IntentRouter(llm=llm)

    # Expression
    tts = PiperTTSEngine(
        model_path=config.tts_model_path,
    )

    # Governance
    conversation_logger = ConversationLogger(
        log_path=config.conversation_log_path,
    )
    acl = ACL()
    identity_store = IdentityStore()
    audit_log = AuditLog(log_path="data/audit.jsonl")

    # Enroll default mock users for ACL verification
    identity_store.enroll(
        FamilyMember(user_id="parent_default", name="Ramesh", role=Role.PARENT)
    )
    identity_store.enroll(
        FamilyMember(user_id="child_default", name="Arjun", role=Role.CHILD)
    )

    # Skill discovery and registry
    from packages.core.skills import (
        AcSkill,
        AssistantSkill,
        CallsSkill,
        CookingSkill,
        FanSkill,
        GeyserSkill,
        HomeworkSkill,
        LightsSkill,
        MemoryAdminSkill,
        MusicSkill,
        PumpSkill,
        RemindersSkill,
        SecuritySkill,
        SensorsSkill,
        SkillRegistry,
        TvSkill,
        WasherSkill,
    )

    skill_registry = SkillRegistry()
    skill_registry.register(LightsSkill(), ["home_control"])
    skill_registry.register(RemindersSkill(), ["timer", "reminder"])
    skill_registry.register(MemoryAdminSkill(), ["memory_store", "memory_recall"])
    skill_registry.register(AssistantSkill(), ["general_chat"])

    # Phase 2 appliance skills
    skill_registry.register(AcSkill(), ["control_ac"])
    skill_registry.register(TvSkill(), ["control_tv"])
    skill_registry.register(GeyserSkill(), ["control_geyser"])
    skill_registry.register(PumpSkill(), ["control_pump"])
    skill_registry.register(WasherSkill(), ["control_washer"])
    skill_registry.register(FanSkill(), ["control_fan"])

    # Extended Phase 2 skills
    skill_registry.register(MusicSkill(), ["play_music"])
    skill_registry.register(CookingSkill(), ["cooking"])
    skill_registry.register(HomeworkSkill(), ["homework"])

    # Phase 3 skills
    sensors_skill = SensorsSkill()
    skill_registry.register(CallsSkill(), ["calls"])
    skill_registry.register(SecuritySkill(), ["security"])
    skill_registry.register(sensors_skill, ["sensors"])

    # Wire Zigbee2MQTT sensor notifications if MQTT is used
    if mqtt_client:
        mqtt_client.register_listener(
            "zigbee2mqtt/",
            lambda topic, payload: sensors_skill.handle_mqtt_message(
                topic, payload, {"notify": wired.notify}
            ),
        )

    return {
        "audio": wired.audio,
        "camera": wired.camera,
        "home": wired.home,
        "power": wired.power,
        "notify": wired.notify,
        "telephony": wired.telephony,
        "mqtt_client": mqtt_client,
        "wakeword": wakeword,
        "vad": vad,
        "stt": stt,
        "llm": llm,
        "memory": memory,
        "intent_router": intent_router,
        "tts": tts,
        "conversation_logger": conversation_logger,
        "acl": acl,
        "identity_store": identity_store,
        "audit_log": audit_log,
        "skill_registry": skill_registry,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="FamilyRobot – Low-cost, local-first companion."
    )
    parser.add_argument(
        "--platform",
        choices=["desktop", "android", "raspberrypi"],
        help="Force execution platform (otherwise auto-detected).",
    )
    parser.add_argument(
        "--config",
        help="Path to custom configuration YAML file.",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s [%(name)s] %(levelname)s %(message)s",
    )

    config = load_config(platform=args.platform)
    logger.info(
        "Platform: %s | Wake word: %s", config.platform, config.system.wake_word
    )

    components = _build_components(config)
    shutdown_event = asyncio.Event()

    def _signal_handler(*_: object) -> None:
        logger.info("Shutdown signal received.")
        shutdown_event.set()

    # Register signal handlers (SIGINT works on Windows; SIGTERM on Unix)
    signal.signal(signal.SIGINT, _signal_handler)
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, _signal_handler)

    try:
        asyncio.run(run_loop(components, shutdown_event=shutdown_event))
    except KeyboardInterrupt:
        logger.info("Interrupted.")

    logger.info("FamilyRobot stopped.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
