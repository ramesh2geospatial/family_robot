# Quality Constitution

This document defines the quality gates, coverage requirements, and architectural standards for the FamilyRobot system. All developers (human or AI) must respect these boundaries.

## 1. Quality Philosophy
- **Local First**: All speech, wakeword detection, and user identification must execute locally.
- **Fail Closed**: All security checks must fail closed. If a command cannot be verified, it is blocked.
- **Audited by Default**: Every privileged action (appliance state toggle, memory write) must be recorded to the audit log.

## 2. Test Coverage Metrics
- **Unit Tests**: Minimum 80% coverage on core libraries (`packages/core/`).
- **Contract Tests**: 100% coverage on hardware adapter ports. Every adapter must satisfy the port protocol tests.
- **Zero Theater**: Mocking is only permitted at the hardware layer (e.g. mic, camera, I2C). Mocking internal logic (like ACL checks, RAG database) to pass tests is forbidden.

## 3. Fitness-to-Purpose Scenarios
- **Scenario A**: Child requests geyser activation → system says "Sorry, only adults can control the geyser" and does not trigger the switch.
- **Scenario B**: Power cut recovery → Pi reboots, battery capacity registers <15% but charging status is "charging" → safe shutdown loop is suppressed.
- **Scenario C**: Concurrent database updates → both succeed or fail gracefully without lockups.
