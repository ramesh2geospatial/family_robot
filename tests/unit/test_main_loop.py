"""
Unit tests for the main orchestrator loop.
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from packages.core.cognition.intent_router import Intent


# We import the module under test after defining mocks
from apps.familyrobot.main_loop import _handle_intent, _speak, run_loop


# ──────────────────────────────────────────────
# Helpers: build a full mock component set
# ──────────────────────────────────────────────

def _mock_components(
    *,
    wake_score: float = 0.0,
    vad_end_after: int = 2,
    transcription: str = "hello",
    intent: Intent | None = None,
    llm_response: str = "Sure thing!",
) -> dict:
    """Create a fully mocked component dict for run_loop."""

    audio = AsyncMock()
    audio.open_input = AsyncMock()
    audio.close = AsyncMock()
    audio.play = AsyncMock()
    _frame_count = {"n": 0}

    async def _read_frame():
        _frame_count["n"] += 1
        return b"\x00" * 1024

    audio.read_frame = AsyncMock(side_effect=_read_frame)

    home = AsyncMock()
    home.set_switch = AsyncMock(return_value=True)

    llm = AsyncMock()
    llm.generate = AsyncMock(return_value=llm_response)

    memory = AsyncMock()
    memory.store = AsyncMock(return_value="abcd1234-0000-0000-0000-000000000000")
    memory.search = AsyncMock(return_value=[{"text": "Aarav birthday March 5", "score": 0.95}])

    tts = AsyncMock()
    tts.synthesize = AsyncMock(return_value=(b"\x00" * 100, 22050))

    wakeword = MagicMock()
    wakeword.predict = MagicMock(return_value=wake_score)

    vad = MagicMock()
    _vad_calls = {"n": 0}
    def _vad_process(chunk):
        _vad_calls["n"] += 1
        if _vad_calls["n"] >= vad_end_after:
            return {"end": _vad_calls["n"]}
        return None
    vad.process_chunk = MagicMock(side_effect=_vad_process)

    stt = MagicMock()
    stt.transcribe = MagicMock(return_value=(transcription, "en"))

    ir = AsyncMock()
    ir.classify = AsyncMock(
        return_value=intent or Intent(name="general_chat", confidence=0.5)
    )

    cl = MagicMock()
    cl.log_interaction = MagicMock()

    return {
        "audio": audio,
        "home": home,
        "llm": llm,
        "memory": memory,
        "tts": tts,
        "wakeword": wakeword,
        "vad": vad,
        "stt": stt,
        "intent_router": ir,
        "conversation_logger": cl,
    }


# ──────────────────────────────────────────────
# _handle_intent unit tests
# ──────────────────────────────────────────────

@pytest.mark.unit
class TestHandleIntent:

    @pytest.mark.asyncio
    async def test_home_control(self) -> None:
        home = AsyncMock()
        home.set_switch = AsyncMock(return_value=True)
        intent = Intent("home_control", 0.9, {"devices": ["geyser"], "action": "on"})
        result = await _handle_intent(intent, "turn on geyser", home, AsyncMock(), AsyncMock())
        assert "geyser" in result.lower()
        home.set_switch.assert_called_once_with("geyser", True)

    @pytest.mark.asyncio
    async def test_memory_store(self) -> None:
        memory = AsyncMock()
        memory.store = AsyncMock(return_value="abc12345-xxxx")
        intent = Intent("memory_store", 0.9, {})
        result = await _handle_intent(intent, "remember x", AsyncMock(), AsyncMock(), memory)
        assert "saved" in result.lower()

    @pytest.mark.asyncio
    async def test_memory_recall(self) -> None:
        memory = AsyncMock()
        memory.search = AsyncMock(return_value=[{"text": "March 5", "score": 0.9}])
        intent = Intent("memory_recall", 0.9, {})
        result = await _handle_intent(intent, "when is birthday", AsyncMock(), AsyncMock(), memory)
        assert "March 5" in result

    @pytest.mark.asyncio
    async def test_memory_recall_empty(self) -> None:
        memory = AsyncMock()
        memory.search = AsyncMock(return_value=[])
        intent = Intent("memory_recall", 0.9, {})
        result = await _handle_intent(intent, "xyz", AsyncMock(), AsyncMock(), memory)
        assert "don't have" in result.lower()

    @pytest.mark.asyncio
    async def test_general_chat(self) -> None:
        llm = AsyncMock()
        llm.generate = AsyncMock(return_value="Here is a joke.")
        intent = Intent("general_chat", 0.5, {})
        result = await _handle_intent(intent, "tell joke", AsyncMock(), llm, AsyncMock())
        assert "joke" in result.lower()

    @pytest.mark.asyncio
    async def test_timer(self) -> None:
        intent = Intent("timer", 0.9, {"duration": {"minutes": 5}})
        result = await _handle_intent(intent, "set timer", AsyncMock(), AsyncMock(), AsyncMock())
        assert "coming soon" in result.lower()


# ──────────────────────────────────────────────
# _speak unit test
# ──────────────────────────────────────────────

@pytest.mark.unit
class TestSpeak:

    @pytest.mark.asyncio
    async def test_speak_calls_tts_and_play(self) -> None:
        tts = AsyncMock()
        tts.synthesize = AsyncMock(return_value=(b"\x00" * 10, 22050))
        audio = AsyncMock()
        await _speak(tts, audio, "hello")
        tts.synthesize.assert_called_once_with("hello")
        audio.play.assert_called_once()

    @pytest.mark.asyncio
    async def test_speak_handles_tts_error(self) -> None:
        tts = AsyncMock()
        tts.synthesize = AsyncMock(side_effect=RuntimeError("TTS broke"))
        audio = AsyncMock()
        # Should not raise
        await _speak(tts, audio, "hello")


# ──────────────────────────────────────────────
# run_loop integration (quick shutdown)
# ──────────────────────────────────────────────

@pytest.mark.unit
class TestRunLoop:

    @pytest.mark.asyncio
    async def test_loop_exits_on_shutdown(self) -> None:
        """Loop should exit cleanly when shutdown_event is set."""
        comps = _mock_components(wake_score=0.0)
        shutdown = asyncio.Event()
        shutdown.set()  # immediate shutdown
        await run_loop(comps, shutdown_event=shutdown)
        comps["audio"].close.assert_called_once()

    @pytest.mark.asyncio
    async def test_loop_calls_conversation_logger(self) -> None:
        """Loop should log the interaction via conversation_logger."""
        comps = _mock_components(wake_score=0.9, vad_end_after=1, transcription="test hello")
        shutdown = asyncio.Event()

        # Set shutdown inside the audio play mock so the loop exits after one speak/log cycle
        comps["audio"].play.side_effect = lambda *args, **kwargs: shutdown.set()

        # Safety fallback: shut down if it runs too long
        async def run_and_stop():
            await asyncio.sleep(0.5)
            shutdown.set()
        asyncio.create_task(run_and_stop())

        await run_loop(comps, shutdown_event=shutdown)
        comps["conversation_logger"].log_interaction.assert_called_once()

