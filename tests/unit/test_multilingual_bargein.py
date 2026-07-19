"""Unit tests for multilingual conversation consistency and barge-in playback control."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from apps.familyrobot.main_loop import _listen_cycle, _handle_intent
from packages.core.skills import SkillContext
from packages.core.governance import ACL, UNKNOWN_USER, AuditLog, IdentityStore
from packages.core.cognition import Intent


@pytest.mark.asyncio
async def test_barge_in_pauses_and_resumes() -> None:
    """If music is playing, detecting wake word should pause it, and resume it after a general query."""
    # 1. Setup mock components
    mock_audio = AsyncMock()
    mock_audio.read_frame = AsyncMock(return_value=b"\x00" * 3200)

    mock_wakeword = MagicMock()
    mock_wakeword.predict.return_value = 0.99  # wake word triggered!

    mock_vad = MagicMock()
    # Return end of speech immediately to avoid long loop
    mock_vad.process_chunk.return_value = {"end": True}

    mock_stt = MagicMock()
    mock_stt.transcribe.return_value = ("hello", "en")

    mock_intent_router = AsyncMock()
    mock_intent_router.classify = AsyncMock(
        return_value=Intent(name="general_chat", confidence=0.9)
    )

    mock_llm = AsyncMock()
    mock_llm.generate = AsyncMock(return_value="Hello there!")

    mock_media_player = AsyncMock()
    mock_media_player.is_playing = MagicMock(return_value=True)  # music is playing!
    mock_media_player.pause = AsyncMock()
    mock_media_player.resume = AsyncMock()

    ports = {"media_player": mock_media_player}

    # 2. Run _listen_cycle
    await _listen_cycle(
        audio=mock_audio,
        home=None,
        llm=mock_llm,
        memory=None,
        tts=AsyncMock(),
        wakeword=mock_wakeword,
        vad=mock_vad,
        stt=mock_stt,
        intent_router=mock_intent_router,
        conversation_logger=None,
        acl=ACL(),
        identity_store=IdentityStore(),
        audit_log=MagicMock(),
        skill_registry=None,
        ports=ports,
        shutdown_event=asyncio.Event(),
    )

    # 3. Assertions
    # Verify it paused the music on wake word detection
    mock_media_player.pause.assert_called_once()
    # Verify it resumed the music after speaking because intent was not stop/pause music
    mock_media_player.resume.assert_called_once()


@pytest.mark.asyncio
async def test_barge_in_no_resume_on_stop() -> None:
    """If the intent is play_music with action stop/pause, it should NOT resume music."""
    # 1. Setup mock components
    mock_audio = AsyncMock()
    mock_audio.read_frame = AsyncMock(return_value=b"\x00" * 3200)

    mock_wakeword = MagicMock()
    mock_wakeword.predict.return_value = 0.99  # wake word triggered!

    mock_vad = MagicMock()
    mock_vad.process_chunk.return_value = {"end": True}

    mock_stt = MagicMock()
    mock_stt.transcribe.return_value = ("stop music", "en")

    mock_intent_router = AsyncMock()
    mock_intent_router.classify = AsyncMock(
        return_value=Intent(name="play_music", confidence=0.9, entities={"action": "stop"})
    )

    mock_llm = AsyncMock()

    mock_media_player = AsyncMock()
    mock_media_player.is_playing = MagicMock(return_value=True)  # music is playing!
    mock_media_player.pause = AsyncMock()
    mock_media_player.resume = AsyncMock()

    # Registry with a mock MusicSkill
    mock_skill_registry = MagicMock()
    mock_skill = AsyncMock()
    from packages.core.skills.base import SkillResult
    mock_skill.execute = AsyncMock(return_value=SkillResult(spoken_response="Stopping music.", success=True))
    mock_skill_registry.get_skill.return_value = mock_skill

    ports = {"media_player": mock_media_player}

    # 2. Run _listen_cycle
    await _listen_cycle(
        audio=mock_audio,
        home=None,
        llm=mock_llm,
        memory=None,
        tts=AsyncMock(),
        wakeword=mock_wakeword,
        vad=mock_vad,
        stt=mock_stt,
        intent_router=mock_intent_router,
        conversation_logger=None,
        acl=ACL(),
        identity_store=IdentityStore(),
        audit_log=MagicMock(),
        skill_registry=mock_skill_registry,
        ports=ports,
        shutdown_event=asyncio.Event(),
    )

    # 3. Assertions
    # Verify it paused the music on wake word detection
    mock_media_player.pause.assert_called_once()
    # Verify it did NOT resume the music because intent was play_music action stop
    mock_media_player.resume.assert_not_called()


@pytest.mark.asyncio
async def test_multilingual_translation_layer() -> None:
    """If user speaks Hindi (lang=hi), English skill responses should be dynamically translated to Hindi."""
    # 1. Setup mock components
    mock_audio = AsyncMock()
    mock_audio.read_frame = AsyncMock(return_value=b"\x00" * 3200)

    mock_wakeword = MagicMock()
    mock_wakeword.predict.return_value = 0.99

    mock_vad = MagicMock()
    mock_vad.process_chunk.return_value = {"end": True}

    mock_stt = MagicMock()
    # User speaks Hindi
    mock_stt.transcribe.return_value = ("लाइट चालू करो", "hi")

    mock_intent_router = AsyncMock()
    mock_intent_router.classify = AsyncMock(
        return_value=Intent(name="home_control", confidence=0.9, entities={"devices": ["light"], "action": "on"})
    )

    # Mock the LLM to translate English response to Hindi
    mock_llm = AsyncMock()
    mock_llm.generate = AsyncMock(return_value="लाइट चालू कर दी है।")

    mock_tts = AsyncMock()

    # Mock Skill Registry returning English response
    mock_skill_registry = MagicMock()
    mock_skill = AsyncMock()
    from packages.core.skills.base import SkillResult
    # English response from skill
    mock_skill.execute = AsyncMock(return_value=SkillResult(spoken_response="Turned on the light.", success=True))
    mock_skill_registry.get_skill.return_value = mock_skill

    # 2. Run _listen_cycle
    await _listen_cycle(
        audio=mock_audio,
        home=None,
        llm=mock_llm,
        memory=None,
        tts=mock_tts,
        wakeword=mock_wakeword,
        vad=mock_vad,
        stt=mock_stt,
        intent_router=mock_intent_router,
        conversation_logger=None,
        acl=ACL(),
        identity_store=IdentityStore(),
        audit_log=MagicMock(),
        skill_registry=mock_skill_registry,
        ports={},
        shutdown_event=asyncio.Event(),
    )

    # 3. Assertions
    # Verify LLM translation was called
    mock_llm.generate.assert_called_once()
    prompt_arg = mock_llm.generate.call_args[1].get("prompt", "")
    assert "Translate" in prompt_arg
    assert "Turned on the light" in prompt_arg

    # Verify TTS spoke the translated Hindi response, not the English one
    mock_tts.synthesize.assert_any_call("लाइट चालू कर दी है।")
