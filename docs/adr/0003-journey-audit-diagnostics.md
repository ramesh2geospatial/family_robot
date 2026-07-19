# ADR 0003: Voice-First Journey Audit & Diagnostics

## Status

Approved

## Context

Family members interacting with the voice assistant may encounter issues such as:
1. Incorrect Speech-to-Text (STT) transcription where the robot misinterprets what was said.
2. Silent Access Control List (ACL) denials where a command is rejected (e.g., a child trying to turn on the geyser) and the user doesn't understand why.
3. Lack of feedback on whether a command successfully executed.

Currently, these events are written to the `ConversationLogger` and `AuditLog` files, but they are only accessible to developers with shell or database access. To provide full transparency and debugging capabilities directly to the family, a secure voice-accessible diagnostics mechanism is needed.

## Decision

We will implement a `JourneyAuditSkill` registered on the `audit_journey` intent. This skill exposes query ports for the append-only `AuditLog` and `ConversationLogger`.

The skill provides three voice-first diagnostics:
1. **Speech Verification ("What did you hear?")**: Queries `ConversationLogger` to read back the previous user turn's raw transcription text.
2. **Access Control Analysis ("Why was my request denied?")**: Queries the recent `AuditLog` logs to explain the most recent rejected ACL check for that user.
3. **Command History ("Show my recent commands")**: Lists recent successful device commands and intent actions.

### Privacy and Security Considerations

1. **Access Isolation**: Audit queries retrieve logs filtered by the active `user_id` context to prevent cross-user leakage of commands/transcriptions, except for the generic default/unknown user context which acts as the shared room context.
2. **Guest Exclusions**: Guests do not have access to RAG memory queries and their history is capped.
3. **No Raw Media exposure**: The diagnostics only repeat transcribed text and metadata, never raw audio or speech wave recordings.

## Consequences

- **Transparency**: Users can immediately diagnose why a command failed by asking a follow-up question.
- **Debugging**: Diagnostics are completely local-first and voice-accessible, requiring no smartphone or companion application connection to troubleshoot voice loop issues.
- **Auditing Overhead**: Very low, as the skill queries small sliding-window in-memory lists or fast database indexes.
