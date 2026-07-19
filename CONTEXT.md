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
