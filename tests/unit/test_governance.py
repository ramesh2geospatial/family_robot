"""
Unit tests for the governance package (Identity, ACL, AuditLog).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from packages.core.governance.acl import ACL, ACLResult
from packages.core.governance.audit_log import AuditLog
from packages.core.governance.conversation_log import ConversationLogger
from packages.core.governance.identity import (
    UNKNOWN_USER,
    FamilyMember,
    IdentityStore,
    Role,
)


# ──────────────────────────────────────────────
# Identity
# ──────────────────────────────────────────────

@pytest.mark.unit
class TestIdentity:

    def test_family_member_creation(self) -> None:
        m = FamilyMember(user_id="u1", name="Aarav", role=Role.CHILD)
        assert m.name == "Aarav"
        assert m.role == Role.CHILD

    def test_identity_store_enroll_and_get(self) -> None:
        store = IdentityStore()
        member = FamilyMember(user_id="u1", name="Papa", role=Role.PARENT)
        store.enroll(member)
        assert store.get("u1").name == "Papa"

    def test_identity_store_unknown_user(self) -> None:
        store = IdentityStore()
        user = store.get("nonexistent")
        assert user is UNKNOWN_USER
        assert user.role == Role.GUEST

    def test_identity_store_list_members(self) -> None:
        store = IdentityStore()
        store.enroll(FamilyMember(user_id="u1", name="A", role=Role.PARENT))
        store.enroll(FamilyMember(user_id="u2", name="B", role=Role.CHILD))
        assert len(store.list_members()) == 2

    def test_mock_identity_fusion(self) -> None:
        store = IdentityStore()
        result = store.identify(face_embedding=[0.1], voice_embedding=[0.2])
        assert result is UNKNOWN_USER


# ──────────────────────────────────────────────
# ACL – Permission Matrix
# ──────────────────────────────────────────────

@pytest.mark.unit
class TestACL:

    @pytest.fixture
    def acl(self) -> ACL:
        return ACL()

    @pytest.fixture
    def parent(self) -> FamilyMember:
        return FamilyMember(user_id="p1", name="Papa", role=Role.PARENT)

    @pytest.fixture
    def adult(self) -> FamilyMember:
        return FamilyMember(user_id="a1", name="Mama", role=Role.ADULT)

    @pytest.fixture
    def teen(self) -> FamilyMember:
        return FamilyMember(user_id="t1", name="Priya", role=Role.TEEN)

    @pytest.fixture
    def child(self) -> FamilyMember:
        return FamilyMember(user_id="c1", name="Aarav", role=Role.CHILD)

    @pytest.fixture
    def guest(self) -> FamilyMember:
        return FamilyMember(user_id="g1", name="Visitor", role=Role.GUEST)

    # ── Tier 1: everyone allowed ──

    def test_lights_allowed_for_all(self, acl: ACL, parent, adult, teen, child, guest) -> None:
        for user in [parent, adult, teen, child, guest]:
            assert acl.check_permission(user, "control_lights").allowed is True

    def test_fan_allowed_for_all(self, acl: ACL, child, guest) -> None:
        assert acl.check_permission(child, "control_fan").allowed is True
        assert acl.check_permission(guest, "control_fan").allowed is True

    # ── Tier 2: teen+ ──

    def test_washer_allowed_for_teen(self, acl: ACL, teen) -> None:
        assert acl.check_permission(teen, "control_washer").allowed is True

    def test_washer_denied_for_child(self, acl: ACL, child) -> None:
        result = acl.check_permission(child, "control_washer")
        assert result.allowed is False
        assert result.spoken_denial != ""

    # ── Tier 3: adult+ ──

    def test_geyser_allowed_for_parent(self, acl: ACL, parent) -> None:
        assert acl.check_permission(parent, "control_geyser").allowed is True

    def test_geyser_allowed_for_adult(self, acl: ACL, adult) -> None:
        assert acl.check_permission(adult, "control_geyser").allowed is True

    def test_geyser_denied_for_teen(self, acl: ACL, teen) -> None:
        result = acl.check_permission(teen, "control_geyser")
        assert result.allowed is False
        assert "adult" in result.spoken_denial.lower()

    def test_geyser_denied_for_child(self, acl: ACL, child) -> None:
        result = acl.check_permission(child, "control_geyser")
        assert result.allowed is False

    def test_geyser_denied_for_guest(self, acl: ACL, guest) -> None:
        result = acl.check_permission(guest, "control_geyser")
        assert result.allowed is False

    def test_pump_denied_for_child(self, acl: ACL, child) -> None:
        result = acl.check_permission(child, "control_pump")
        assert result.allowed is False

    def test_ac_denied_for_teen(self, acl: ACL, teen) -> None:
        result = acl.check_permission(teen, "control_ac")
        assert result.allowed is False

    # ── Memory writes ──

    def test_memory_write_allowed_for_parent(self, acl: ACL, parent) -> None:
        assert acl.check_permission(parent, "memory_write").allowed is True

    def test_memory_write_allowed_for_guest(self, acl: ACL, guest) -> None:
        # Per spec: guest CAN write memory
        assert acl.check_permission(guest, "memory_write").allowed is True

    def test_memory_write_denied_for_child(self, acl: ACL, child) -> None:
        result = acl.check_permission(child, "memory_write")
        assert result.allowed is False

    # ── Device lookup ──

    def test_check_device_geyser(self, acl: ACL, child) -> None:
        result = acl.check_device(child, "geyser")
        assert result.allowed is False

    def test_check_device_light(self, acl: ACL, child) -> None:
        result = acl.check_device(child, "light")
        assert result.allowed is True

    # ── Intent-level check ──

    def test_check_intent_home_control_denied(self, acl: ACL, child) -> None:
        result = acl.check_intent(child, "home_control", {"devices": ["geyser"]})
        assert result.allowed is False

    def test_check_intent_home_control_allowed(self, acl: ACL, child) -> None:
        result = acl.check_intent(child, "home_control", {"devices": ["light"]})
        assert result.allowed is True

    def test_check_intent_memory_store_denied_child(self, acl: ACL, child) -> None:
        result = acl.check_intent(child, "memory_store")
        assert result.allowed is False

    def test_check_intent_general_chat_allowed(self, acl: ACL, child) -> None:
        result = acl.check_intent(child, "general_chat")
        assert result.allowed is True

    # ── Unknown permission ──

    def test_unknown_permission_allows(self, acl: ACL, child) -> None:
        result = acl.check_permission(child, "some_future_permission")
        assert result.allowed is True


# ──────────────────────────────────────────────
# Audit Log
# ──────────────────────────────────────────────

@pytest.mark.unit
class TestAuditLog:

    def test_record_and_read(self, tmp_path: Path) -> None:
        log = AuditLog(log_path=str(tmp_path / "audit.jsonl"))
        log.record(event="acl_check", user_id="u1", user_role="child",
                   allowed=False, details={"device": "geyser"})
        log.record(event="device_command", user_id="p1", user_role="parent",
                   allowed=True, details={"device": "light", "action": "on"})

        entries = log.read_recent(10)
        assert len(entries) == 2
        assert entries[0]["event"] == "acl_check"
        assert entries[0]["allowed"] is False
        assert entries[1]["event"] == "device_command"

    def test_read_empty(self, tmp_path: Path) -> None:
        log = AuditLog(log_path=str(tmp_path / "empty.jsonl"))
        assert log.read_recent() == []

    def test_read_recent_limits(self, tmp_path: Path) -> None:
        log = AuditLog(log_path=str(tmp_path / "many.jsonl"))
        for i in range(10):
            log.record(event=f"event_{i}", user_id="u1")
        entries = log.read_recent(3)
        assert len(entries) == 3
        assert entries[-1]["event"] == "event_9"


# ──────────────────────────────────────────────
# Conversation Logger
# ──────────────────────────────────────────────

@pytest.mark.unit
class TestConversationLogger:

    def test_log_interaction_and_read(self, tmp_path: Path) -> None:
        log = ConversationLogger(log_path=str(tmp_path / "conversations.jsonl"))
        log.log_interaction(
            user_id="u1",
            user_role="parent",
            audio_duration_s=2.5,
            detected_language="en",
            raw_text="hello puppy",
            intent="general_chat",
            intent_confidence=0.9,
            response_text="Hello!",
            processing_time_s=0.15,
            tts_engine="pyttsx3"
        )

        entries = log.get_recent(5)
        assert len(entries) == 1
        assert entries[0]["user_id"] == "u1"
        assert entries[0]["input_text"] == "hello puppy"
        assert entries[0]["response_text"] == "Hello!"
        assert entries[0]["processing_time_s"] == 0.15

    def test_get_recent_empty(self, tmp_path: Path) -> None:
        log = ConversationLogger(log_path=str(tmp_path / "empty.jsonl"))
        assert log.get_recent() == []

