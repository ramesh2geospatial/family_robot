"""
Unit tests for the VAD and TTS volume ducking system.
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from packages.core.media.media_player import MediaPlayer
from packages.core.perception.vad import VoiceActivityDetector


# ── 1. VoiceActivityDetector.get_speech_probability Tests ──
def test_vad_get_speech_probability_empty() -> None:
    vad = VoiceActivityDetector()
    assert vad.get_speech_probability(b"") == 0.0
    assert vad.get_speech_probability(None) == 0.0


def test_vad_get_speech_probability_mocked() -> None:
    vad = VoiceActivityDetector()
    mock_model = MagicMock()
    mock_model.return_value = MagicMock(item=lambda: 0.85)
    vad.model = mock_model

    # 1024 bytes of dummy audio data
    dummy_audio = b"\x00" * 1024
    prob = vad.get_speech_probability(dummy_audio)
    assert prob == 0.85


# ── 2. MediaPlayer Ducking state and IPC Tests ──
@pytest.mark.asyncio
async def test_media_player_ducking_states() -> None:
    player = MediaPlayer()
    player._process = MagicMock()  # Mock running process
    player._process.poll = MagicMock(return_value=None)  # is_playing = True

    mock_send = MagicMock(return_value=True)
    player._send_ipc_command = mock_send

    # Test ducking
    await player.duck(pct=40, duration=0.1)
    assert player._is_ducked is True
    # Verify set_property command was sent via IPC
    mock_send.assert_called_with({"command": ["set_property", "volume", 40]})

    # Test unducking
    await player.unduck()
    assert player._is_ducked is False
    mock_send.assert_called_with({"command": ["set_property", "volume", 100]})


@pytest.mark.asyncio
async def test_media_player_ducking_auto_cancel_on_stop() -> None:
    player = MediaPlayer()
    player._process = MagicMock()
    player._process.poll = MagicMock(return_value=None)
    player._send_ipc_command = MagicMock(return_value=True)

    await player.duck(pct=50, duration=1.0)
    assert player._unduck_task is not None
    assert player._is_ducked is True

    # Calling stop should cancel the task and reset state
    await player.stop()
    assert player._is_ducked is False
    assert player._unduck_task is None


# ── 3. Main Loop Integration Tests ──
@pytest.mark.asyncio
async def test_main_loop_speak_ducking() -> None:
    from apps.familyrobot.main_loop import _speak

    mock_tts = AsyncMock()
    mock_tts.synthesize.return_value = (b"\x00" * 3200, 16000)

    mock_audio = AsyncMock()

    mock_media = AsyncMock()
    mock_media.is_playing.return_value = True
    mock_media.duck = AsyncMock()
    mock_media.unduck = AsyncMock()

    await _speak(mock_tts, mock_audio, "Hello there", media_player=mock_media)

    # Speak-ducking should have triggered duck() before speech and unduck() after
    mock_media.duck.assert_called_once_with(pct=50, duration=10.0)
    mock_media.unduck.assert_called_once()
