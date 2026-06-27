# Confirmed Defects

This document records the confirmed defects identified in Phase 3 code review.

### BUG-001: Main Loop Bypasses ACL Validation
- Primary requirement: REQ-001
- Covers: [REQ-001/cell-home_control-voice_orchestrator, REQ-001/cell-memory_store-voice_orchestrator]
- Consolidation rationale: Both intents are routed inside the same `_handle_intent` dispatcher block in `apps/familyrobot/main_loop.py`. A single fix in the orchestrator pipeline resolves both security omissions.
- File:Line: apps/familyrobot/main_loop.py:150-160
- Class: security-bypass
- Description: The orchestrator main loop classifies voice commands but routes them directly to state modifiers without calling the ACL access check.
- Expected behavior: Every privileged intent must invoke `acl.check_intent(user, intent.name, intent.entities)` and speak a polite denial if rejected.
- Actual behavior: Commands are executed directly for any voice input.

### BUG-002: FastAPI Webapp Command Bypasses ACL Check
- Primary requirement: REQ-002
- Covers: [REQ-002/cell-home_control-webapp, REQ-002/cell-memory_store-webapp]
- Consolidation rationale: Both routes are endpoints within the same `packages/core/webapp/app.py` FastAPI app.
- File:Line: packages/core/webapp/app.py:157-177
- Class: security-bypass
- Description: Web companion endpoints dispatch device control switch changes to the hardware adapters directly, bypassing the security policy matrix.
- Expected behavior: REST request payloads must be checked against user roles before toggling devices.
- Actual behavior: REST API requests execute switches unconditionally.

### BUG-003: Pi Power Monitor Safe Shutdown Loops While Charging
- Primary requirement: REQ-005
- Covers: [REQ-005/cell-battery_monitoring-raspberrypi]
- File:Line: packages/adapters/raspberrypi/power.py:73-85
- Class: contract-mismatch
- Description: The Pi battery monitor loop checks percentage but does not verify charging status, triggering safe shutdown loops on power cuts recovery.
- Expected behavior: Callback triggers only when battery is low and discharging.
- Actual behavior: Callback triggers on any low battery level.

### BUG-004: Fail-Open Policy for Unregistered Permissions
- Primary requirement: REQ-003
- File:Line: packages/core/governance/acl.py:101-106
- Class: security-logic
- Description: ACL returns `allowed=True` if a permission is not defined in the matrix.
- Expected behavior: Unrecognized permissions must fail closed and return `allowed=False`.
- Actual behavior: Misspelled permissions fail open.
