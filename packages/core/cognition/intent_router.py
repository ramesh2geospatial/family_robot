"""
Rule-based intent router with optional LLM fallback.

Classifies user utterances into actionable intents for the
FamilyRobot pipeline.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Optional, Protocol

logger = logging.getLogger(__name__)


# ---- LLM port protocol (for optional fallback) ----
class _LLMProtocol(Protocol):
    async def generate(self, prompt: str, *, system: str = "", max_tokens: int = 512,
                       temperature: float = 0.7, stop: list[str] | None = None) -> str: ...


# ---- Data structures ----

@dataclass
class Intent:
    """Classified user intent."""

    name: str
    confidence: float
    entities: dict = field(default_factory=dict)


# ---- Keyword rules ----

_HOME_KEYWORDS = [
    "turn on", "turn off", "switch on", "switch off",
    "geyser", "light", "fan", "ac", "pump", "heater",
    "washer", "washing machine", "lamp",
]
_MEMORY_STORE_KEYWORDS = [
    "remember that", "remember this", "save this", "note that",
    "don't forget", "keep in mind",
]
_MEMORY_RECALL_KEYWORDS = [
    "when is", "what is", "do you remember", "recall",
    "what did", "tell me about", "who is",
]
_TIMER_KEYWORDS = [
    "set timer", "set a timer", "remind me in", "alarm in",
    "start a timer", "countdown",
]
_REMINDER_KEYWORDS = [
    "remind me to", "reminder for", "set a reminder",
    "set reminder",
]

_DEVICE_NAMES = [
    "geyser", "light", "fan", "ac", "pump", "heater",
    "washer", "washing machine", "lamp", "tv", "television",
]


def _extract_devices(text: str) -> list[str]:
    """Extract known device names from text."""
    lower = text.lower()
    return [d for d in _DEVICE_NAMES if d in lower]


def _extract_on_off(text: str) -> Optional[bool]:
    """Determine if user wants to turn something on or off."""
    lower = text.lower()
    if "turn off" in lower or "switch off" in lower:
        return False
    if "turn on" in lower or "switch on" in lower:
        return True
    return None


_DURATION_RE = re.compile(
    r"(\d+)\s*(second|sec|minute|min|hour|hr)s?", re.IGNORECASE
)


def _extract_duration(text: str) -> Optional[dict]:
    """Extract a duration like '5 minutes' from text."""
    match = _DURATION_RE.search(text)
    if not match:
        return None
    value = int(match.group(1))
    unit = match.group(2).lower()
    if unit in ("sec", "second"):
        return {"seconds": value}
    if unit in ("min", "minute"):
        return {"minutes": value}
    if unit in ("hr", "hour"):
        return {"hours": value}
    return None


class IntentRouter:
    """Classify user text into an Intent using keyword rules.

    Falls back to LLM classification when no rule matches and an
    ``llm`` port is provided.
    """

    def __init__(self, llm: Optional[_LLMProtocol] = None) -> None:
        self._llm = llm

    def _match_keywords(self, text: str) -> Optional[Intent]:
        lower = text.lower()

        # Order matters: more specific intents first
        for kw in _MEMORY_STORE_KEYWORDS:
            if kw in lower:
                return Intent(name="memory_store", confidence=0.9, entities={})

        for kw in _MEMORY_RECALL_KEYWORDS:
            if kw in lower:
                return Intent(name="memory_recall", confidence=0.9, entities={})

        for kw in _TIMER_KEYWORDS:
            if kw in lower:
                dur = _extract_duration(text)
                entities: dict = {}
                if dur:
                    entities["duration"] = dur
                return Intent(name="timer", confidence=0.9, entities=entities)

        for kw in _REMINDER_KEYWORDS:
            if kw in lower:
                return Intent(name="reminder", confidence=0.85, entities={})

        for kw in _HOME_KEYWORDS:
            if kw in lower:
                devices = _extract_devices(text)
                on_off = _extract_on_off(text)
                entities = {}
                if devices:
                    entities["devices"] = devices
                if on_off is not None:
                    entities["action"] = "on" if on_off else "off"
                return Intent(
                    name="home_control", confidence=0.9, entities=entities
                )

        return None

    async def classify(self, text: str) -> Intent:
        """Classify *text* into an ``Intent``."""
        if not text or not text.strip():
            return Intent(name="general_chat", confidence=0.0, entities={})

        rule_match = self._match_keywords(text)
        if rule_match:
            logger.debug("Rule match: %s (%.2f)", rule_match.name, rule_match.confidence)
            return rule_match

        # Optional LLM fallback
        if self._llm is not None:
            try:
                return await self._llm_classify(text)
            except Exception as exc:
                logger.warning("LLM intent fallback failed: %s", exc)

        return Intent(name="general_chat", confidence=0.5, entities={})

    async def _llm_classify(self, text: str) -> Intent:
        """Use LLM to classify when rules don't match."""
        system = (
            "You are an intent classifier. Classify the user message into exactly "
            "one of: home_control, memory_store, memory_recall, timer, reminder, "
            "general_chat. Respond with ONLY the intent name, nothing else."
        )
        result = await self._llm.generate(  # type: ignore[union-attr]
            text, system=system, max_tokens=20, temperature=0.1
        )
        intent_name = result.strip().lower().replace(" ", "_")
        valid = {"home_control", "memory_store", "memory_recall",
                 "timer", "reminder", "general_chat"}
        if intent_name not in valid:
            intent_name = "general_chat"
        return Intent(name=intent_name, confidence=0.7, entities={})
