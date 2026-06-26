"""
Identity and user management for FamilyRobot.

Defines the FamilyMember model, role hierarchy, and a mock identity
fusion layer (face+voice → user) for the Desktop MVP.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

logger = logging.getLogger(__name__)


class Role(str, Enum):
    """Family member roles – ordered from most to least privileged."""

    PARENT = "parent"
    ADULT = "adult"
    TEEN = "teen"
    CHILD = "child"
    GUEST = "guest"


@dataclass
class FamilyMember:
    """Represents a recognised family member."""

    user_id: str
    name: str
    role: Role
    language: str = "en"
    face_embedding: Optional[list[float]] = field(default=None, repr=False)
    voice_embedding: Optional[list[float]] = field(default=None, repr=False)


# Default "unknown" user used when identification fails
UNKNOWN_USER = FamilyMember(
    user_id="unknown",
    name="Someone",
    role=Role.GUEST,
)


class IdentityStore:
    """In-memory store of enrolled family members.

    For the Desktop MVP this is populated at start-up from config.
    Future steps will add face/voice enrollment via the PWA.
    """

    def __init__(self) -> None:
        self._members: dict[str, FamilyMember] = {}

    def enroll(self, member: FamilyMember) -> None:
        """Add or update a family member."""
        self._members[member.user_id] = member
        logger.info("Enrolled %s (%s) as %s", member.name, member.user_id, member.role.value)

    def get(self, user_id: str) -> FamilyMember:
        """Return a member by ID, or UNKNOWN_USER."""
        return self._members.get(user_id, UNKNOWN_USER)

    def list_members(self) -> list[FamilyMember]:
        """Return all enrolled members."""
        return list(self._members.values())

    def identify(
        self,
        *,
        face_embedding: Optional[list[float]] = None,
        voice_embedding: Optional[list[float]] = None,
    ) -> FamilyMember:
        """Fuse face + voice embeddings to identify a user.

        Desktop MVP: always returns UNKNOWN_USER (no real biometrics yet).
        Future: cosine-match against enrolled embeddings.
        """
        # Placeholder – real fusion in Step 11 (speakerID) / Step 13 (faceID)
        logger.debug("identity_fusion called (mock); returning UNKNOWN_USER")
        return UNKNOWN_USER
