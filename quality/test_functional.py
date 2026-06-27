"""
Functional tests derived from requirements for the FamilyRobot system.
"""

import pytest
import os
from pathlib import Path
from packages.core.governance.acl import ACL, Role
from packages.core.governance.identity import FamilyMember
from packages.core.memory.memory_store import MemoryStore

@pytest.mark.functional
def test_acl_roles_and_denials() -> None:
    """Validate ACL matrix roles and custom denials."""
    acl = ACL()
    child = FamilyMember(user_id="c1", name="Arjun", role=Role.CHILD)
    parent = FamilyMember(user_id="p1", name="Ramesh", role=Role.PARENT)
    
    # lights should be accessible to child
    assert acl.check_permission(child, "control_lights").allowed is True
    
    # geyser control must be denied for child
    res_geyser = acl.check_permission(child, "control_geyser")
    assert res_geyser.allowed is False
    assert "only adults" in res_geyser.spoken_denial
    
    # geyser control allowed for parent
    assert acl.check_permission(parent, "control_geyser").allowed is True

@pytest.mark.functional
def test_fail_open_evaluation() -> None:
    """Validate that undefined permissions evaluate properly."""
    acl = ACL()
    child = FamilyMember(user_id="c1", name="Arjun", role=Role.CHILD)
    
    # Undefined permission -> warning is logged and currently allowed by default (fail-open)
    res = acl.check_permission(child, "some_unknown_permission")
    assert res.allowed is True
