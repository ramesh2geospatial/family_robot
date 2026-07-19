# Context Glossary (FamilyRobot Domain Vocabulary)

This glossary contains the canonical terminology and domain concepts used throughout the FamilyRobot assistant system. It focuses on the language and semantics of the household companion space.

### General Domain Concepts

*   **Companion Robot / Assistant**: The local household helper executing voice, home control, memory, and media routines for the family members.
*   **Family Member**: One of the registered household occupants, identified by name, role, and language preferences.
*   **Role**: The permission tier assigned to a Family Member (e.g., Parent, Child, Guest) regulating access to high-power appliances or sensitive features.
*   **User Journey**: The end-to-end flow of interaction between a Family Member and the Robot, spanning wake-word detection, speech capture, intent routing, governance checks, action execution, and verbal expression.

### Interaction & Audit Vocabulary

*   **Wake Word**: The verbal trigger phrase ("Hello Puppy") that initializes voice capture and transitions the Robot from passive polling to active listening.
*   **Acoustic Barge-in**: The ability of the Robot to pause ongoing media playback when the Wake Word is detected, enabling interruption during active audio outputs.
*   **Intent**: The classified meaning of a Family Member's spoken query or command (e.g., control_geyser, play_music).
*   **ACL check**: The policy check verifying if a Family Member's Role is authorized to execute a requested Intent.
*   **Audit Log**: The secure, append-only ledger recording security-sensitive operations, ACL checks, and executed device commands.
*   **Conversation Log**: The diagnostic record capturing voice query transcribing inputs, matched intents, processing times, and spoken response texts.
*   **Interaction Audit / Voice Audit**: The diagnostic query checking logs to explain to a family member what speech was heard, why a command succeeded/failed, or why an action was denied.
*   **Auto-Memory Extraction**: The background process of automatically extracting declarative facts from conversation turns using the local LLM.
*   **Memory Deduplication**: The process of checking semantic similarity before storing a new memory to prevent duplicate records and database bloat.

### Intelligence & Context Vocabulary

*   **Context Builder**: The unified prompt assembler that constructs token-budgeted system prompts with identity, time awareness, RAG memories, personality, and active state sections.
*   **Tool-Use / Function Calling**: The ability of the LLM to invoke registered tools (control devices, play music, set timers) by emitting structured JSON instead of plain text during general chat.
*   **Tool Registry**: The catalog of callable tools with name, description, parameter schema, and async handler function, available to the LLM.
*   **Tool Executor**: The component that parses tool-call JSON from LLM output, validates parameters, enforces ACL, and executes the tool handler.
*   **Proactive Engine**: The background intelligence engine that periodically evaluates time, state, and memory patterns to generate unsolicited suggestions (morning greetings, device warnings, bedtime reminders).
*   **Personality Profile**: Role-appropriate behavioral instructions (child-friendly, elder-respectful, guest-welcoming) injected into the LLM system prompt.
*   **Acknowledgment Phrase**: A short spoken phrase ("Let me think…") played immediately after STT completes, before LLM inference, to eliminate the silence gap.
*   **Structured Intent Classification**: The LLM fallback intent classification that returns JSON with both intent name and extracted entities, replacing the old name-only classification.
