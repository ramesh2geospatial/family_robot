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
    async def generate(
        self,
        prompt: str,
        *,
        system: str = "",
        max_tokens: int = 512,
        temperature: float = 0.7,
        stop: list[str] | None = None,
    ) -> str: ...


# ---- Data structures ----


@dataclass
class Intent:
    """Classified user intent."""

    name: str
    confidence: float
    entities: dict = field(default_factory=dict)


# ---- Keyword rules ----

_HOME_KEYWORDS = [
    "turn on",
    "turn off",
    "switch on",
    "switch off",
    "geyser",
    "light",
    "fan",
    "ac",
    "pump",
    "heater",
    "washer",
    "washing machine",
    "lamp",
    "tv",
    "television",
    "volume",
    "source",
]
_MEMORY_STORE_KEYWORDS = [
    "remember that",
    "remember this",
    "save this",
    "note that",
    "don't forget",
    "keep in mind",
]
_MEMORY_RECALL_KEYWORDS = [
    "when is",
    "what is",
    "do you remember",
    "recall",
    "what did",
    "tell me about",
    "who is",
]
_TIMER_KEYWORDS = [
    "set timer",
    "set a timer",
    "remind me in",
    "alarm in",
    "start a timer",
    "countdown",
]
_REMINDER_KEYWORDS = [
    "remind me to",
    "reminder for",
    "set a reminder",
    "set reminder",
]
_CALLS_KEYWORDS = ["call ", "phone ", "dial "]
_SECURITY_KEYWORDS = ["security check", "check security", "anyone outside"]
_SENSORS_KEYWORDS = ["sensor status", "door status", "doors locked"]
_MUSIC_KEYWORDS = ["play ", "pause music", "stop music", "next song", "music", "gana"]
_COOKING_KEYWORDS = ["recipe", "cook", "convert", "step", "pudhchi", "pudhe"]
_HOMEWORK_KEYWORDS = ["explain", "solve", "quiz", "question about"]

_DEVICE_NAMES = [
    "geyser",
    "light",
    "fan",
    "ac",
    "pump",
    "heater",
    "washer",
    "washing machine",
    "lamp",
    "tv",
    "television",
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


_DURATION_RE = re.compile(r"(\d+)\s*(second|sec|minute|min|hour|hr)s?", re.IGNORECASE)


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


def _extract_temp(text: str) -> Optional[int]:
    """Extract temperature value near AC commands."""
    match = re.search(r"(?:to|at|temp|temperature)\s*(\d{2})", text, re.IGNORECASE)
    if match:
        return int(match.group(1))
    return None


def _extract_mode(text: str) -> Optional[str]:
    """Extract mode from text (cool, heat, dry, fan)."""
    lower = text.lower()
    for m in ("cool", "heat", "dry", "fan"):
        if m in lower:
            return m
    return None


def _extract_source(text: str) -> Optional[str]:
    """Extract source name from text."""
    match = re.search(r"source\s+(?:on\s+tv\s+)?(?:to\s+)?(\w+)", text, re.IGNORECASE)
    if match:
        return match.group(1)
    return None


def _extract_cooking_convert(text: str) -> Optional[dict]:
    """Extract amount, unit, and target unit for cooking conversions."""
    match = re.search(
        r"convert\s+(\d+(?:\.\d+)?)\s*(\w+)\s+to\s+(\w+)", text, re.IGNORECASE
    )
    if match:
        return {
            "amount": match.group(1),
            "unit": match.group(2),
            "target_unit": match.group(3),
        }
    return None


def _extract_cooking_recipe(text: str) -> Optional[str]:
    """Extract recipe name from cooking queries."""
    match = re.search(
        r"(?:cook|recipe for|recipe|start recipe)\s+(.+)", text, re.IGNORECASE
    )
    if match:
        return match.group(1).strip().rstrip("?.!")
    return None


def _extract_homework_explain(text: str) -> Optional[dict]:
    """Extract concept and grade from homework explanation requests."""
    match = re.search(r"explain\s+(.+?)\s+for\s+grade\s+(\d+)", text, re.IGNORECASE)
    if match:
        return {"concept": match.group(1).strip(), "grade": match.group(2)}
    match = re.search(r"explain\s+(.+)", text, re.IGNORECASE)
    if match:
        return {"concept": match.group(1).strip(), "grade": "5"}
    return None


def _extract_homework_solve(text: str) -> Optional[str]:
    """Extract the math problem string to solve."""
    match = re.search(r"(?:solve|solve math problem)\s+(.+)", text, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return None


def _extract_homework_quiz(text: str) -> Optional[str]:
    """Extract topic name for quizzes."""
    match = re.search(r"quiz\s+(?:me\s+)?(?:on|about)\s+(.+)", text, re.IGNORECASE)
    if match:
        return match.group(1).strip().rstrip("?.!")
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
        for kw in _CALLS_KEYWORDS:
            if kw in lower:
                contact = text[lower.index(kw) + len(kw) :].strip().rstrip("?.!")
                return Intent(
                    name="calls", confidence=0.9, entities={"contact": contact}
                )

        for kw in _SECURITY_KEYWORDS:
            if kw in lower:
                return Intent(name="security", confidence=0.9, entities={})

        for kw in _SENSORS_KEYWORDS:
            if kw in lower:
                return Intent(name="sensors", confidence=0.9, entities={})

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

        for kw in _MUSIC_KEYWORDS:
            if kw in lower:
                action = "play"
                song = ""
                if "pause" in lower:
                    action = "pause"
                elif "stop" in lower:
                    action = "stop"
                elif "next" in lower:
                    action = "next"
                elif lower.startswith("play "):
                    song = text[5:].strip().rstrip("?.!")
                return Intent(
                    name="play_music",
                    confidence=0.9,
                    entities={"action": action, "song": song},
                )

        for kw in _COOKING_KEYWORDS:
            if kw in lower:
                if "next step" in lower or "next" in lower:
                    return Intent(
                        name="cooking",
                        confidence=0.9,
                        entities={"intent_id": "cooking.next"},
                    )
                conv = _extract_cooking_convert(text)
                if conv:
                    conv["intent_id"] = "cooking.convert"
                    return Intent(name="cooking", confidence=0.9, entities=conv)
                rec = _extract_cooking_recipe(text)
                if rec:
                    return Intent(
                        name="cooking",
                        confidence=0.9,
                        entities={"intent_id": "cooking.recipe", "recipe": rec},
                    )

        for kw in _HOMEWORK_KEYWORDS:
            if kw in lower:
                if "quiz" in lower:
                    topic = _extract_homework_quiz(text)
                    if topic:
                        return Intent(
                            name="homework",
                            confidence=0.9,
                            entities={"intent_id": "homework.quiz", "topic": topic},
                        )
                if "solve" in lower:
                    prob = _extract_homework_solve(text)
                    if prob:
                        return Intent(
                            name="homework",
                            confidence=0.9,
                            entities={"intent_id": "homework.solve", "problem": prob},
                        )
                exp = _extract_homework_explain(text)
                if exp:
                    exp["intent_id"] = "homework.explain"
                    return Intent(name="homework", confidence=0.9, entities=exp)

        for kw in _HOME_KEYWORDS:
            if kw in lower:
                devices = _extract_devices(text)
                on_off = _extract_on_off(text)
                entities = {}
                if on_off is not None:
                    entities["action"] = "on" if on_off else "off"

                # Check for specific appliances to route to dedicated skills
                if len(devices) > 1:
                    entities["devices"] = devices
                    return Intent(
                        name="home_control", confidence=0.9, entities=entities
                    )

                if "ac" in devices:
                    entities["temp"] = _extract_temp(text)
                    entities["mode"] = _extract_mode(text)
                    return Intent(name="control_ac", confidence=0.9, entities=entities)

                if "tv" in devices or "television" in devices:
                    entities["source"] = _extract_source(text)
                    if "volume up" in lower or "volume_up" in lower:
                        entities["action"] = "volume_up"
                    elif "volume down" in lower or "volume_down" in lower:
                        entities["action"] = "volume_down"
                    return Intent(name="control_tv", confidence=0.9, entities=entities)

                if "geyser" in devices or "heater" in devices:
                    return Intent(
                        name="control_geyser", confidence=0.9, entities=entities
                    )

                if "pump" in devices:
                    return Intent(
                        name="control_pump", confidence=0.9, entities=entities
                    )

                if "washer" in devices or "washing machine" in devices:
                    return Intent(
                        name="control_washer", confidence=0.9, entities=entities
                    )

                if "fan" in devices:
                    speed = None
                    speed_match = re.search(
                        r"(?:speed\s+)?([1-5])", text, re.IGNORECASE
                    )
                    if speed_match and "fan" in lower:
                        speed = int(speed_match.group(1))
                    entities["speed"] = speed
                    return Intent(name="control_fan", confidence=0.9, entities=entities)

                if devices:
                    entities["devices"] = devices
                return Intent(name="home_control", confidence=0.9, entities=entities)

        return None

    async def classify(self, text: str) -> Intent:
        """Classify *text* into an ``Intent``."""
        if not text or not text.strip():
            return Intent(name="general_chat", confidence=0.0, entities={})

        rule_match = self._match_keywords(text)
        if rule_match:
            logger.debug(
                "Rule match: %s (%.2f)", rule_match.name, rule_match.confidence
            )
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
            "one of: home_control, control_ac, control_tv, control_geyser, control_pump, "
            "control_washer, control_fan, play_music, cooking, homework, memory_store, "
            "memory_recall, timer, reminder, calls, security, sensors, general_chat. "
            "Respond with ONLY the intent name, nothing else."
        )
        result = await self._llm.generate(  # type: ignore[union-attr]
            text, system=system, max_tokens=20, temperature=0.1
        )
        intent_name = result.strip().lower().replace(" ", "_")
        valid = {
            "home_control",
            "control_ac",
            "control_tv",
            "control_geyser",
            "control_pump",
            "control_washer",
            "control_fan",
            "play_music",
            "cooking",
            "homework",
            "memory_store",
            "memory_recall",
            "timer",
            "reminder",
            "calls",
            "security",
            "sensors",
            "general_chat",
        }
        if intent_name not in valid:
            intent_name = "general_chat"
        return Intent(name=intent_name, confidence=0.7, entities={})
