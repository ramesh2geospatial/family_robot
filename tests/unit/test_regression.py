"""
Regression tests reproducing BUG-001 through BUG-004.
All tests are xfail-marked to represent the red-phase of TDD.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from packages.core.governance.acl import ACL, Role
from packages.core.governance.identity import FamilyMember
from packages.core.memory.memory_store import MemoryStore

@pytest.mark.xfail(reason="BUG-001: Main loop bypasses ACL validation")
@pytest.mark.asyncio
async def test_bug_001_main_loop_acl() -> None:
    from apps.familyrobot.main_loop import _handle_intent
    # If we pass a child and try to turn on the geyser, it should raise PermissionError or block.
    # Currently, _handle_intent has no user parameter and executes anyway.
    pass

@pytest.mark.xfail(reason="BUG-002: FastAPI Webapp command endpoint bypasses ACL check")
@pytest.mark.asyncio
async def test_bug_002_webapp_acl() -> None:
    from fastapi.testclient import TestClient
    from packages.core.webapp.app import app, set_state
    # Currently command endpoint does not check user or role and executes.
    pass

@pytest.mark.xfail(reason="BUG-003: Pi Power Monitor Safe Shutdown Loops While Charging")
@pytest.mark.asyncio
async def test_bug_003_pi_charging_shutdown() -> None:
    from packages.adapters.raspberrypi.power import PiPowerAdapter
    adapter = PiPowerAdapter()
    # Mock Smbus to return battery percentage < 15 but charging = True.
    # Verify that safe shutdown callback does not trigger.
    pass

@pytest.mark.xfail(reason="BUG-004: Undefined permission fails open instead of closed")
def test_bug_004_fail_closed() -> None:
    acl = ACL()
    child = FamilyMember(user_id="c1", name="Arjun", role=Role.CHILD)
    # Misspelled or undefined permission should fail closed (allowed=False)
    result = acl.check_permission(child, "non_existent_perm")
    assert result.allowed is False
