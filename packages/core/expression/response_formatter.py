"""
Response formatter for spoken output.

Cleans LLM / handler output into natural spoken text suitable for TTS.
"""

from __future__ import annotations

import re

_MAX_WORDS = 200

# Markdown artefacts to strip
_MD_PATTERNS = [
    (re.compile(r"```[\s\S]*?```"), ""),       # fenced code blocks
    (re.compile(r"`([^`]+)`"), r"\1"),          # inline code
    (re.compile(r"\*\*([^*]+)\*\*"), r"\1"),    # bold
    (re.compile(r"\*([^*]+)\*"), r"\1"),         # italic
    (re.compile(r"^#{1,6}\s+", re.MULTILINE), ""),  # headings
    (re.compile(r"^[-*]\s+", re.MULTILINE), ""),     # bullet lists
    (re.compile(r"^\d+\.\s+", re.MULTILINE), ""),    # numbered lists
    (re.compile(r"\[([^\]]+)\]\([^)]+\)"), r"\1"),   # links → text
]

_INTENT_PREFIXES: dict[str, str] = {
    "home_control": "Done! ",
    "memory_store": "Got it! I'll remember that. ",
    "timer": "Timer set! ",
    "reminder": "Reminder saved! ",
}


def format_response(raw_text: str | None, intent_name: str = "general_chat") -> str:
    """Clean *raw_text* into spoken-friendly output.

    - Strips markdown syntax.
    - Truncates to ~200 words.
    - Prepends a contextual politeness prefix for certain intents.
    """
    if not raw_text:
        return "I'm not sure what to say."

    text = raw_text

    # Strip markdown
    for pattern, replacement in _MD_PATTERNS:
        text = pattern.sub(replacement, text)

    # Collapse whitespace
    text = re.sub(r"\s+", " ", text).strip()

    # Truncate
    words = text.split()
    if len(words) > _MAX_WORDS:
        text = " ".join(words[:_MAX_WORDS]) + "…"

    # Add intent-specific prefix
    prefix = _INTENT_PREFIXES.get(intent_name, "")
    if prefix and not text.startswith(prefix):
        text = prefix + text

    return text
