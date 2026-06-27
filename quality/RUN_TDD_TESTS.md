# TDD Verification Protocol

This protocol defines the Red-Green TDD verification cycles for reproducing and patching confirmed defects.

## 1. TDD Cycle: SQLite Write Lock Timeout (BUG-001)
- **Red Phase**: Trigger multiple concurrent writes to the SQLite database without lock timeout configuration. Assert that a `sqlite3.OperationalError` is raised.
- **Patch**: Add `timeout=10.0` to `sqlite3.connect` options.
- **Green Phase**: Concurrent write attempts resolve successfully within the timeout window.

## 2. TDD Cycle: Pi UPS Charging Loop (BUG-002)
- **Red Phase**: Set Pi battery percentage to 10% and charge state to true. Run `PiPowerAdapter` monitor loop and assert that the safe-shutdown callback triggers.
- **Patch**: Check charging status before triggering callback.
- **Green Phase**: Monitor loop runs with low battery while charging without executing safe-shutdown callbacks.
