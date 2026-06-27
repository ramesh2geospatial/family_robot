# Code Review Protocol

This protocol guides reviewers through a structured three-pass inspection of the FamilyRobot codebase.

## Pass 1: Structural and Syntax Scrutiny
- **Unused Imports & Variables**: Scan for dead imports (e.g. `Optional` in governance packages).
- **Resource Management**: Check if SQLite connections and audio devices are guaranteed to close under exception pathways (try/finally blocks).

## Pass 2: Requirement Verification
- **REQ-001 (Main Loop ACL)**: Inspect `apps/familyrobot/main_loop.py` to ensure `ACL.check_intent()` is called.
- **REQ-002 (Webapp API ACL)**: Inspect `packages/core/webapp/app.py` to ensure `/api/device/command` runs role checks.
- **REQ-003 (Fail-Closed ACL)**: Verify that `packages/core/governance/acl.py` fails closed for unrecognized permissions.
- **REQ-004 (Audit Logging)**: Ensure `AuditLog.record()` is called on every privileged control event.

## Pass 3: Consistency Check
- **Power monitors**: Diff the `_monitor_loop` implementation of `PiPowerAdapter` and `TermuxPowerAdapter` to ensure charging checks match.
