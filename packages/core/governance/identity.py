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


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    from math import sqrt

    if len(a) != len(b) or not a or not b:
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = sqrt(sum(x * x for x in a))
    norm_b = sqrt(sum(x * x for x in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


class IdentityStore:
    """Database-backed store of enrolled family members.

    Initializes schemas and provides persistent CRUD operations.
    """

    def __init__(self, *, persistence: Optional[PersistenceContext] = None) -> None:
        from packages.core.memory.persistence import PersistenceContext

        self.persistence = persistence or PersistenceContext(":memory:")

    def enroll(self, member: FamilyMember) -> None:
        """Add or update a family member in the persistent database."""
        import json
        from datetime import datetime, timezone

        face_blob = (
            json.dumps(member.face_embedding)
            if member.face_embedding is not None
            else None
        )
        voice_blob = (
            json.dumps(member.voice_embedding)
            if member.voice_embedding is not None
            else None
        )
        now = datetime.now(timezone.utc).isoformat()

        with self.persistence.get_connection() as conn:
            conn.execute(
                """
                INSERT INTO family_members (user_id, name, role, language, face_embedding, voice_embedding, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    name=excluded.name,
                    role=excluded.role,
                    language=excluded.language,
                    face_embedding=excluded.face_embedding,
                    voice_embedding=excluded.voice_embedding
                """,
                (
                    member.user_id,
                    member.name,
                    member.role.value,
                    member.language,
                    face_blob,
                    voice_blob,
                    now,
                ),
            )
            conn.commit()
        logger.info(
            "Enrolled %s (%s) as %s", member.name, member.user_id, member.role.value
        )

    def get(self, user_id: str) -> FamilyMember:
        """Return a member by ID, or UNKNOWN_USER."""
        import json

        with self.persistence.get_connection() as conn:
            row = conn.execute(
                "SELECT name, role, language, face_embedding, voice_embedding FROM family_members WHERE user_id = ?",
                (user_id,),
            ).fetchone()

        if not row:
            return UNKNOWN_USER

        name, role_val, language, face_json, voice_json = row
        face_emb = json.loads(face_json) if face_json else None
        voice_emb = json.loads(voice_json) if voice_json else None
        return FamilyMember(
            user_id=user_id,
            name=name,
            role=Role(role_val),
            language=language,
            face_embedding=face_emb,
            voice_embedding=voice_emb,
        )

    def list_members(self) -> list[FamilyMember]:
        """Return all enrolled members."""
        import json

        with self.persistence.get_connection() as conn:
            rows = conn.execute(
                "SELECT user_id, name, role, language, face_embedding, voice_embedding FROM family_members"
            ).fetchall()

        members = []
        for user_id, name, role_val, language, face_json, voice_json in rows:
            face_emb = json.loads(face_json) if face_json else None
            voice_emb = json.loads(voice_json) if voice_json else None
            members.append(
                FamilyMember(
                    user_id=user_id,
                    name=name,
                    role=Role(role_val),
                    language=language,
                    face_embedding=face_emb,
                    voice_embedding=voice_emb,
                )
            )
        return members

    def identify(
        self,
        *,
        face_embedding: Optional[list[float]] = None,
        voice_embedding: Optional[list[float]] = None,
    ) -> FamilyMember:
        """Fuse face + voice embeddings to identify a user.

        Compares against enrolled family members using average cosine similarity.
        """
        if not face_embedding and not voice_embedding:
            return UNKNOWN_USER

        best_member = UNKNOWN_USER
        best_score = -1.0

        members = self.list_members()
        for member in members:
            score = 0.0
            contribs = 0

            if face_embedding and member.face_embedding:
                face_score = _cosine_similarity(face_embedding, member.face_embedding)
                score += face_score
                contribs += 1

            if voice_embedding and member.voice_embedding:
                voice_score = _cosine_similarity(voice_embedding, member.voice_embedding)
                score += voice_score
                contribs += 1

            if contribs > 0:
                avg_score = score / contribs
                if avg_score > best_score and avg_score > 0.7:  # 0.7 confidence threshold
                    best_score = avg_score
                    best_member = member

        return best_member
