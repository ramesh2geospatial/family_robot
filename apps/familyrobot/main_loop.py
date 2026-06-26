"""
Main orchestrator loop for FamilyRobot.

Runs the full pipeline: wake-word → VAD → STT → intent → action → TTS → play.
"""

from __future__ import annotations

import asyncio
import logging
import time

from packages.core.expression.response_formatter import format_response

logger = logging.getLogger(__name__)

_WAKE_THRESHOLD = 0.5
_FALLBACK_MSG = "Sorry, I didn't catch that. Could you try again?"


async def run_loop(
    components: dict,
    *,
    shutdown_event: asyncio.Event | None = None,
) -> None:
    """Run the FamilyRobot voice assistant loop.

    *components* is a dict with keys:
        audio, home, llm, memory, tts, wakeword, vad, stt, intent_router

    The loop runs until *shutdown_event* is set or cancelled.
    """
    if shutdown_event is None:
        shutdown_event = asyncio.Event()

    audio = components["audio"]
    home = components["home"]
    llm = components["llm"]
    memory = components["memory"]
    tts = components["tts"]
    wakeword = components["wakeword"]
    vad = components["vad"]
    stt = components["stt"]
    intent_router = components["intent_router"]

    logger.info("Opening audio input…")
    await audio.open_input(samplerate=16000)
    logger.info("FamilyRobot loop started. Listening for wake word…")

    conversation_logger = components.get("conversation_logger")

    try:
        while not shutdown_event.is_set():
            await _listen_cycle(
                audio, home, llm, memory, tts,
                wakeword, vad, stt, intent_router,
                conversation_logger,
                shutdown_event,
            )
    except asyncio.CancelledError:
        logger.info("Loop cancelled.")
    finally:
        await audio.close()
        logger.info("Audio closed. Loop exited.")


async def _listen_cycle(
    audio, home, llm, memory, tts,
    wakeword, vad, stt, intent_router,
    conversation_logger,
    shutdown_event: asyncio.Event,
) -> None:
    """One wake-listen-respond cycle."""

    # Flush any stale audio accumulated from speech/processing before starting a new listening block
    await audio.flush()

    # 1. Wait for wake word
    frame = await audio.read_frame()
    score = await asyncio.to_thread(wakeword.predict, frame)
    if score < _WAKE_THRESHOLD:
        return  # keep polling

    logger.info("Wake word detected (score=%.2f). Listening…", score)

    # 2. VAD → accumulate speech frames
    speech_frames: list[bytes] = []
    listening = True
    vad.reset() if hasattr(vad, "reset") else None

    while listening and not shutdown_event.is_set():
        chunk = await audio.read_frame()
        result = await asyncio.to_thread(vad.process_chunk, chunk)
        speech_frames.append(chunk)

        if result and "end" in result:
            listening = False
        # Safety: stop after ~15 s of speech (240 frames × 64 ms ≈ 15 s)
        if len(speech_frames) > 240:
            logger.warning("Speech too long; forcing STT.")
            listening = False

    if not speech_frames:
        return

    # 3. Transcribe
    start_time = time.perf_counter()
    all_audio = b"".join(speech_frames)
    try:
        text, lang = await asyncio.to_thread(stt.transcribe, all_audio)
    except Exception as exc:
        logger.error("STT failed: %s", exc)
        await _speak(tts, audio, _FALLBACK_MSG)
        if conversation_logger:
            processing_time = time.perf_counter() - start_time
            conversation_logger.log_interaction(
                raw_text="<STT_FAILED>",
                response_text=_FALLBACK_MSG,
                processing_time_s=processing_time,
                audio_duration_s=len(speech_frames) * 0.1,
                tts_engine="piper" if getattr(tts, "_use_piper", False) else "pyttsx3"
            )
        return

    if not text or not text.strip():
        logger.info("Empty transcription, ignoring.")
        if conversation_logger:
            processing_time = time.perf_counter() - start_time
            conversation_logger.log_interaction(
                detected_language=lang,
                raw_text="<EMPTY>",
                response_text="",
                processing_time_s=processing_time,
                audio_duration_s=len(speech_frames) * 0.1,
                tts_engine="none"
            )
        return

    logger.info("Transcribed: '%s' [%s]", text, lang)

    # 4-7. Intent → action → format → speak
    try:
        intent = await intent_router.classify(text)
        logger.info("Intent: %s (%.2f) entities=%s", intent.name, intent.confidence, intent.entities)

        raw_response = await _handle_intent(intent, text, home, llm, memory)
        response = format_response(raw_response, intent.name)
    except Exception as exc:
        logger.error("Processing failed: %s", exc, exc_info=True)
        response = _FALLBACK_MSG

    logger.info("Robot response: %s", response)
    await _speak(tts, audio, response)

    if conversation_logger:
        processing_time = time.perf_counter() - start_time
        conversation_logger.log_interaction(
            detected_language=lang,
            raw_text=text,
            intent=intent.name if 'intent' in locals() else "unknown",
            intent_confidence=intent.confidence if 'intent' in locals() else 0.0,
            response_text=response,
            processing_time_s=processing_time,
            audio_duration_s=len(speech_frames) * 0.1,
            tts_engine="piper" if getattr(tts, "_use_piper", False) else "pyttsx3"
        )


async def _handle_intent(intent, text: str, home, llm, memory) -> str:
    """Route intent to the appropriate handler and return raw text."""

    if intent.name == "home_control":
        devices = intent.entities.get("devices", [])
        action = intent.entities.get("action", "on")
        on = action == "on"
        results = []
        for dev in devices:
            ok = await home.set_switch(dev, on)
            state_word = "on" if on else "off"
            results.append(f"Turned {state_word} the {dev}." if ok
                           else f"Failed to control {dev}.")
        return " ".join(results) if results else f"I'll try to handle that."

    if intent.name == "memory_store":
        mem_id = await memory.store(text)
        return f"Saved (id {mem_id[:8]})."

    if intent.name == "memory_recall":
        hits = await memory.search(text, k=3)
        if hits:
            top = hits[0]
            return top["text"]
        return "I don't have anything saved about that."

    if intent.name in ("timer", "reminder"):
        return "I've noted that. Timer and reminder support is coming soon."

    # general_chat fallback
    system = (
        "You are FamilyRobot, a helpful family assistant for an Indian household. "
        "Keep answers concise, warm, and family-friendly."
    )
    return await llm.generate(text, system=system)


async def _speak(tts, audio, text: str) -> None:
    """Synthesise and play *text*."""
    try:
        pcm, sr = await tts.synthesize(text)
        await audio.play(pcm, sr)
    except Exception as exc:
        logger.error("TTS/play failed: %s", exc)
