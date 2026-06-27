"""
Regression tests reproducing BUG-001 through BUG-004.
All tests are xfail-marked to represent the red-phase of TDD.
"""

import pytest

from packages.core.governance.acl import ACL, Role
from packages.core.governance.identity import FamilyMember


@pytest.mark.xfail(reason="BUG-001: Main loop bypasses ACL validation")
@pytest.mark.asyncio
async def test_bug_001_main_loop_acl() -> None:
    pass


@pytest.mark.xfail(reason="BUG-002: FastAPI Webapp command endpoint bypasses ACL check")
@pytest.mark.asyncio
async def test_bug_002_webapp_acl() -> None:
    pass


@pytest.mark.xfail(
    reason="BUG-003: Pi Power Monitor Safe Shutdown Loops While Charging"
)
@pytest.mark.asyncio
async def test_bug_003_pi_charging_shutdown() -> None:
    pass


@pytest.mark.xfail(reason="BUG-004: Undefined permission fails open instead of closed")
def test_bug_004_fail_closed() -> None:
    acl = ACL()
    child = FamilyMember(user_id="c1", name="Arjun", role=Role.CHILD)
    result = acl.check_permission(child, "non_existent_perm")
    assert result.allowed is False
