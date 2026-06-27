# Testable Requirements

This document defines the core functional requirements and use cases for the FamilyRobot system.

## 1. Project Overview
FamilyRobot is a voice-first, local-first family companion and home automation assistant for an 8-member Indian family. It runs on a shared codebase across Desktop, Android, and Raspberry Pi 5.

### System Actors
- **Family Member**: The user (Parent, Adult, Teen, Child) interacting via voice or the companion PWA.
- **Guest**: An unauthenticated or visiting user.
- **Orchestrator**: The voice loop coordinator.
- **FastAPI Webapp**: The PWA backend service.
- **Home Integration Adapters**: Tasmota, Kasa, lgpio relays, and Broadlink blasters.

---

## 2. Use Cases

### UC-01: Control Home Appliance via Voice
- **Actor**: Family Member (Parent, Adult, Teen, Child, Guest)
- **Preconditions**: Wake word detected.
- **Flow**: User says "turn on the living room light." System classifies intent as `home_control`. System runs ACL check, confirms role permission, and executes switch toggle.
- **Postconditions**: Appliance changes state. Action recorded to the audit log.

### UC-02: Prevent Child from Turning On Geyser
- **Actor**: Child
- **Preconditions**: Wake word detected.
- **Flow**: Child says "turn on the geyser." System classifies intent as `home_control`. System identifies user as child, runs ACL check, blocks command, and speaks polite denial.
- **Postconditions**: Geyser state remains unchanged. Denied action logged.

### UC-03: Control Appliance via Companion PWA Dashboard
- **Actor**: Family Member
- **Preconditions**: User authorized and loaded dashboard.
- **Flow**: User clicks toggle on dashboard. Webapp submits POST request to command router. System validates authorization and commands device.
- **Postconditions**: Device changes state.

### UC-04: Log Privilege Events to Append-Only Log
- **Actor**: Orchestrator
- **Preconditions**: Command processing starts.
- **Flow**: System writes interaction parameters to audit file.
- **Postconditions**: Write completes.

### UC-05: Query Memories via Voice
- **Actor**: Family Member
- **Preconditions**: Wake word detected.
- **Flow**: User queries memory. System searches SQLite and speaks top hit.
- **Postconditions**: Result spoken.

---

## 3. Requirements

### REQ-001: Central ACL Verification in Orchestrator Loop
- **Pattern**: whitelist
- **Tier**: 3
- **Functional section**: Governance
- **Description**: The orchestrator main loop must run the ACL permission check against identified users before executing any `home_control` or `memory_store` actions.
- **User story**: As a parent, I want the system to check user permissions before executing voice commands so that children cannot trigger unauthorized changes.
- **Implementation note**: Main loop must call `acl.check_intent(user, intent.name, intent.entities)`.
- **Conditions of satisfaction**:
  - Voice command from parent is allowed.
  - Voice command from child for geyser is blocked.
- **Use cases**: UC-01, UC-02
- **Specificity**: specific

### REQ-002: PWA REST API Device Control ACL Protection
- **Pattern**: whitelist
- **Tier**: 3
- **Functional section**: Webapp
- **Description**: The FastAPI POST endpoint `/api/device/command` must run the ACL permission checker against the active user's credentials and role before routing to the home adapter.
- **User story**: As a parent, I want the webapp commands to be role-checked so that guests cannot toggle restricted appliances.
- **Conditions of satisfaction**:
  - Request with guest role to toggle geyser fails with 403.
- **Use cases**: UC-01, UC-02
- **Specificity**: specific

### REQ-003: Fail-Closed ACL Evaluator
- **Tier**: 3
- **Functional section**: Governance
- **Description**: The ACL permission evaluator must fail closed (return `allowed=False`) when encountering unregistered or undefined permissions.
- **Conditions of satisfaction**:
  - `check_permission` returns False for misspelled or custom permissions.
- **Specificity**: specific

### REQ-004: Mandatory Audit Logging of Privileged Actions
- **Tier**: 3
- **Functional section**: Governance
- **Description**: All successful or denied device commands and memory store actions must write an audit record to the `AuditLog`.
- **Conditions of satisfaction**:
  - `AuditLog.record` is invoked on each control action.
- **Specificity**: specific

### REQ-005: Charging-Aware UPS Power Monitoring
- **Pattern**: parity
- **Tier**: 3
- **Functional section**: Hardware Adapters
- **Description**: The Raspberry Pi power monitor must suppress safe-shutdown warnings if the battery is actively charging.
- **Conditions of satisfaction**:
  - `PiPowerAdapter` battery callback does not fire if charging is active.
- **Specificity**: specific

### REQ-006: Cosine Similarity Vector Length Verification
- **Tier**: 3
- **Functional section**: Memory
- **Description**: The vector memory store similarity calculator must raise a `ValueError` if the length of vectors differs, instead of silently truncating.
- **Conditions of satisfaction**:
  - Comparing 384-dim vector with 128-dim raises ValueError.
- **Specificity**: specific
