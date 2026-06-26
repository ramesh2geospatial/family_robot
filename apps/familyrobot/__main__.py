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
from packages.core.memory import MemoryStore
from packages.core.perception import SpeechToText, VoiceActivityDetector, WakeWordDetector

logger = logging.getLogger(__name__)


def _build_components(config: AppConfig) -> dict:
    """Wire all components from *config* into a single dict."""
    wired = wire_components(config)

    # Perception
    wakeword = WakeWordDetector(wake_word=config.system.wake_word)
    vad = VoiceActivityDetector()
    stt = SpeechToText()

    # Cognition
    llm = LlamaLLMClient(
        model_path=getattr(config, "llm_model_path", "models/llama-3.2-3b.Q4_K_M.gguf"),
    )
    memory = MemoryStore(
        db_path=getattr(config, "memory_db_path", "data/memory.db"),
    )
    intent_router = IntentRouter(llm=llm)

    # Expression
    tts = PiperTTSEngine(
        model_path=getattr(config, "tts_model_path", None),
    )

    return {
        "audio": wired.audio,
        "camera": wired.camera,
        "home": wired.home,
        "power": wired.power,
        "notify": wired.notify,
        "wakeword": wakeword,
        "vad": vad,
        "stt": stt,
        "llm": llm,
        "memory": memory,
        "intent_router": intent_router,
        "tts": tts,
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
    logger.info("Platform: %s | Wake word: %s", config.platform, config.system.wake_word)

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
