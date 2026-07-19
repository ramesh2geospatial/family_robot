# ADR 0004: Asynchronous Auto-Memory Extraction

## Status

Approved

## Context

Currently, the FamilyRobot companion assistant only records permanent memories when a family member explicitly says a prefix command like "remember that X". If a user naturally mentions a fact during general conversation (e.g. "My favorite sport is cricket"), the assistant fails to retain this context for future conversation turns.

We want to introduce a mechanism to automatically ingest and store useful family-specific facts in the background, without requiring explicit "remember that" phrasing.

## Decision

We will implement an asynchronous **Auto-Memory Extraction** background task (`extract_and_store_memories`) that runs after every dialog turn. 

The design is constrained by the following guidelines:
1. **Asynchronous execution**: To preserve a fast time-to-first-token response latency for the voice loop, the fact extraction prompt is spawned as a background task (`asyncio.create_task`) after the TTS response begins/finishes.
2. **Local LLM Prompting**: We instruct the local GGUF model with a specialized system prompt `FACT_EXTRACTION_SYSTEM` to extract only concise, third-person declarative facts (e.g. "Arjun likes ginger tea") from the conversation, or return `NONE` if no useful long-term facts are found.
3. **Role Security Enforcement**: Skip auto-memory extraction entirely if the speaking user's role is `guest`, since guests are not authorized to write to the permanent RAG memory store.
4. **Memory Deduplication**: Before persisting any extracted fact, query `MemoryStore.search(fact, k=1)`. If a highly similar hit (>0.85 similarity score) exists, the fact is skipped to avoid redundant entries and database bloat.
5. **Intent Exclusions**: Skip extraction for meta-level intents like `memory_store`, `memory_recall`, and `audit_journey` to prevent saving the robot's own diagnostic dialog history.

## Consequences

- **Enhanced Personalization**: The assistant can organically learn user preferences and schedules over time during normal chat.
- **System Resource Efficiency**: The in-memory deduplication check prevents database growth from repeated phrases.
- **Privacy Preservation**: Guest users are completely restricted from writing auto-extracted data.
