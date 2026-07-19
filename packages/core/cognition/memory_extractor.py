"""
Memory extraction from active user dialogue turns.
Analyzes dialogue turns in the background, extracts declarative facts,
checks for duplicates in the MemoryStore, and persists them.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

FACT_EXTRACTION_SYSTEM = (
    "You are a background fact-extraction assistant for FamilyRobot. "
    "Your job is to analyze the dialog and extract key, permanent facts about the family "
    "(such as preferences, schedules, birthdays, and likes/dislikes) and return them as concise, declarative third-person facts. "
    "Follow these rules strictly:\n"
    "1. Extract ONLY long-term, useful facts. Ignore temporary conversational comments, greetings, or filler.\n"
    "2. Format each fact as a simple declarative sentence in English, one per line (e.g., 'Arjun starts school at 8 AM').\n"
    "3. Use the family member's name instead of pronouns.\n"
    "4. If no long-term facts were mentioned, respond ONLY with the word 'NONE'."
)


async def extract_and_store_memories(
    llm: Any,
    memory_store: Any,
    user: Any,
    user_text: str,
    robot_response: str,
) -> None:
    """Extracts facts from a dialogue turn in the background and stores them in the memory store."""
    # 1. Role Security Check: Guests write no memory
    if user and hasattr(user, "role") and user.role.value == "guest":
        logger.debug("[MemoryExtractor] Skip extraction: User is a guest.")
        return

    user_name = user.name if (user and hasattr(user, "name")) else "Someone"

    # Construct dialogue context
    prompt = (
        f"User ({user_name}): {user_text}\n"
        f"Robot: {robot_response}\n\n"
        "Extract any permanent facts about the family from this turn. Remember, return ONLY facts or 'NONE'."
    )

    try:
        logger.debug("[MemoryExtractor] Running background fact extraction...")
        raw_output = await llm.generate(
            prompt,
            system=FACT_EXTRACTION_SYSTEM,
            max_tokens=256,
            temperature=0.1,
        )

        output = raw_output.strip()
        if not output or output.upper() == "NONE" or "none" in output.lower():
            logger.debug("[MemoryExtractor] No new facts extracted.")
            return

        lines = [line.strip() for line in output.split("\n") if line.strip()]
        for line in lines:
            # Clean up line formatting (e.g. leading dashes, numbers)
            cleaned = line.lstrip("-*• 1234567890. ").strip()
            if not cleaned or cleaned.upper() == "NONE":
                continue

            # 2. De-duplication Check
            # Search memory store for similar facts
            hits = await memory_store.search(cleaned, k=1)
            is_duplicate = False
            if hits:
                top_hit = hits[0]
                score = top_hit.get("score", 0.0)
                if score > 0.85:
                    logger.info(
                        "[MemoryExtractor] Skipping duplicate fact: '%s' (similarity=%.2f, hit='%s')",
                        cleaned,
                        score,
                        top_hit.get("text"),
                    )
                    is_duplicate = True

            if not is_duplicate:
                logger.info("[MemoryExtractor] Storing new extracted fact: '%s'", cleaned)
                await memory_store.store(
                    cleaned,
                    meta={"extracted": True, "source": "local_llm_auto"},
                )
    except Exception as exc:
        logger.error("[MemoryExtractor] Memory extraction failed: %s", exc, exc_info=True)
