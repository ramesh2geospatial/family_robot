"""
Personality engine for FamilyRobot.

Generates role-appropriate personality instructions that are injected
into the LLM system prompt based on the user's role, interaction
history, and cultural context.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)

# ── Personality profiles by family role ──
_ROLE_PERSONAS: dict[str, str] = {
    "child": (
        " When speaking to this child, use simple vocabulary and short sentences. "
        "Be encouraging ('Great question, beta!'). Use playful analogies. "
        "Never use complex jargon. Be patient and supportive."
    ),
    "teen": (
        " This is a teenager. Be casual but informative. "
        "It's okay to use light humor. Be respectful of their independence. "
        "Keep answers concise — teens don't like long lectures."
    ),
    "adult": (
        " Speaking to an adult family member. Be helpful and conversational. "
        "Give clear, practical answers. It's fine to include details."
    ),
    "parent": (
        " Speaking to a parent/head of household. Be respectful and thorough. "
        "Include relevant context. Proactively mention safety concerns."
    ),
    "elder": (
        " Speaking to an elder family member. Use respectful forms. "
        "Add 'ji' suffix when addressing them. Be more formal and patient. "
        "Speak clearly and avoid slang."
    ),
    "guest": (
        " This is a guest. Be polite and welcoming. "
        "Keep answers helpful but don't share private family information."
    ),
}

# ── Indian cultural calendar (major festivals) ──
_FESTIVALS: dict[str, list[str]] = {
    # Month-Day → list of festival names
    # These are approximate dates; real dates depend on lunar calendar
    "01-14": ["Makar Sankranti"],
    "01-26": ["Republic Day"],
    "03-08": ["Maha Shivaratri"],
    "03-25": ["Holi"],
    "04-14": ["Ambedkar Jayanti", "Baisakhi"],
    "08-15": ["Independence Day"],
    "08-26": ["Janmashtami"],
    "09-07": ["Ganesh Chaturthi"],
    "10-02": ["Gandhi Jayanti"],
    "10-12": ["Dussehra"],
    "10-24": ["Diwali"],
    "11-01": ["Diwali (Padwa)"],
    "11-15": ["Guru Nanak Jayanti"],
    "12-25": ["Christmas"],
}


def get_personality_block(
    *,
    user_role: str = "unknown",
    user_name: str = "Someone",
) -> str:
    """Generate a personality instruction block for the system prompt.

    Args:
        user_role: The family role of the current speaker.
        user_name: The name of the current speaker.

    Returns:
        A string to append to the system prompt.
    """
    parts: list[str] = []

    # Role-based persona
    persona = _ROLE_PERSONAS.get(user_role.lower(), _ROLE_PERSONAS.get("adult", ""))
    if persona:
        parts.append(persona)

    # Festival greeting (if today is a festival)
    festival = _get_todays_festival()
    if festival:
        parts.append(
            f" Today is {festival}! If appropriate, wish the user "
            f"a happy {festival}."
        )

    return "".join(parts)


def _get_todays_festival() -> Optional[str]:
    """Return the name of today's festival, if any."""
    today_key = datetime.now().strftime("%m-%d")
    festivals = _FESTIVALS.get(today_key)
    if festivals:
        return ", ".join(festivals)
    return None
