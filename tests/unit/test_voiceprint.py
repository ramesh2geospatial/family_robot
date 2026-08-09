"""
Unit tests for VoiceprintEncoder and Tiered Identity Resolution.
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from packages.core.governance.acl import ACL
from packages.core.governance.identity import FamilyMember, IdentityStore, Role, UNKNOWN_USER
from packages.core.perception.voiceprint import EMBEDDING_DIM, VoiceprintEncoder


# ── 1. VoiceprintEncoder Tests ──
def test_voiceprint_encoder_empty_audio() -> None:
    encoder = VoiceprintEncoder()
    emb = encoder.encode(b"")
    assert len(emb) == EMBEDDING_DIM
    assert all(v == 0.0 for v in emb)


def test_voiceprint_encoder_valid_audio() -> None:
    encoder = VoiceprintEncoder()
    # 1 second of 16kHz 16-bit mono audio (32,000 bytes)
    dummy_audio = b"\x12\x34" * 16000
    emb = encoder.encode(dummy_audio)

    assert len(emb) == EMBEDDING_DIM
    # Test L2 normalization
    norm = sum(x * x for x in emb) ** 0.5
    assert pytest.approx(norm, abs=1e-3) == 1.0


# ── 2. IdentityStore Embedding Matching Tests ──
def test_identity_store_voiceprint_matching() -> None:
    store = IdentityStore()
    encoder = VoiceprintEncoder()

    # Create dummy voice audio for Ramesh
    ramesh_audio = b"\x20\x40" * 16000
    ramesh_emb = encoder.encode(ramesh_audio)

    member = FamilyMember(
        user_id="ramesh_123",
        name="Ramesh",
        role=Role.PARENT,
        voice_embedding=ramesh_emb,
    )
    store.enroll(member)

    # Identical voice audio should match Ramesh
    matched = store.identify(voice_embedding=ramesh_emb)
    assert matched.user_id == "ramesh_123"
    assert matched.name == "Ramesh"
    assert matched.role == Role.PARENT

    # Distorted/random embedding should fail threshold (>0.70) and return UNKNOWN_USER
    different_emb = [0.0] * EMBEDDING_DIM
    different_emb[5] = 1.0
    unmatched = store.identify(voice_embedding=different_emb)
    assert unmatched.user_id == UNKNOWN_USER.user_id


# ── 3. Main Loop Tiered Identity Resolution Tests ──
@pytest.mark.asyncio
async def test_main_loop_tiered_identity_voiceprint() -> None:
    from apps.familyrobot.main_loop import _listen_cycle

    encoder = VoiceprintEncoder()
    dummy_audio = b"\x20\x40" * 16000
    ramesh_emb = encoder.encode(dummy_audio)

    identity_store = IdentityStore()
    identity_store.enroll(
        FamilyMember(
            user_id="ramesh_parent",
            name="Ramesh",
            role=Role.PARENT,
            voice_embedding=ramesh_emb,
        )
    )

    mock_audio = AsyncMock()
    mock_audio.read_frame = AsyncMock(return_value=dummy_audio)

    mock_wakeword = MagicMock()
    mock_wakeword.predict.return_value = 0.95  # wake word detected

    mock_vad = MagicMock()
    mock_vad.process_chunk.return_value = {"end": True}
    mock_vad.get_speech_probability.return_value = 0.0

    mock_stt = MagicMock()
    mock_stt.transcribe.return_value = ("turn on geyser", "en")

    mock_intent_router = AsyncMock()
    mock_intent_router.classify.return_value = MagicMock(
        name="control_geyser", confidence=0.95, entities={}
    )

    mock_skill_registry = MagicMock()
    mock_skill = AsyncMock()
    from packages.core.skills.base import SkillResult
    mock_skill.execute.return_value = SkillResult(spoken_response="Geyser on.", success=True)
    mock_skill_registry.get_skill.return_value = mock_skill

    ports = {
        "voiceprint_encoder": encoder,
        "media_player": None,
    }

    mock_acl = MagicMock(spec=ACL)
    mock_acl.check_intent.return_value = MagicMock(allowed=True, reason="OK")

    await _listen_cycle(
        audio=mock_audio,
        home=None,
        llm=AsyncMock(),
        memory=None,
        tts=AsyncMock(),
        wakeword=mock_wakeword,
        vad=mock_vad,
        stt=mock_stt,
        intent_router=mock_intent_router,
        conversation_logger=None,
        acl=mock_acl,
        identity_store=identity_store,
        audit_log=MagicMock(),
        skill_registry=mock_skill_registry,
        ports=ports,
        shutdown_event=asyncio.Event(),
    )

    # ACL check should have been called with user='Ramesh' (Role.PARENT) who passed voiceprint identification!
    assert mock_acl.check_intent.called
    user_arg = mock_acl.check_intent.call_args[0][0]
    assert user_arg.name == "Ramesh"
    assert user_arg.role == Role.PARENT
