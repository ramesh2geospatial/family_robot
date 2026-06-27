# Coverage Matrix

This matrix maps functional requirements to their corresponding verification tests.

| Requirement ID | Description | Verifying Test Case | Status |
| :--- | :--- | :--- | :--- |
| **REQ-001** | Loop ACL verification | `tests/unit/test_main_loop.py` | Covered |
| **REQ-002** | Webapp command ACL protection | `tests/unit/test_webapp.py` | Covered |
| **REQ-003** | Fail-closed ACL evaluator | `tests/unit/test_governance.py` | Covered |
| **REQ-004** | Mandatory audit logging | `tests/unit/test_governance.py` | Covered |
| **REQ-005** | Charging-aware power monitor | `tests/contracts/test_pi_adapters.py` | Covered |
| **REQ-006** | Vector length check | `tests/unit/test_memory.py` | Covered |
