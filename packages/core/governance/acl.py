"""
Role-based access control (ACL) for FamilyRobot.

Implements the permission matrix from skills-catalog.md:

| Action group              | parent | adult | teen | child | guest |
|---------------------------|--------|-------|------|-------|-------|
| lights/fan/music/info     |   ✅   |  ✅   |  ✅  |  ✅   |  ✅   |
| AC / TV                   |   ✅   |  ✅   |  ❌  |  ❌   |  ❌   |
| geyser / water pump       |   ✅   |  ✅   |  ❌  |  ❌   |  ❌   |
| washing machine           |   ✅   |  ✅   |  ✅  |  ❌   |  ❌   |
| calls / WhatsApp          |   ✅   |  ✅   |  ❌  |  ❌   |  ❌   |
| memory writes             |   ✅   |  ✅   |  ✅  |  ❌   |  ✅   |
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

from packages.core.governance.identity import FamilyMember, Role

logger = logging.getLogger(__name__)


@dataclass
class ACLResult:
    """Result of an ACL check."""

    allowed: bool
    reason: str = ""
    spoken_denial: str = ""


# ── Permission matrix ────────────────────────────────────────────────

# Maps (permission_group) → set of roles that are ALLOWED
_PERMISSION_MATRIX: dict[str, set[Role]] = {
    # Tier 1: everyone
    "control_lights": {Role.PARENT, Role.ADULT, Role.TEEN, Role.CHILD, Role.GUEST},
    "control_fan": {Role.PARENT, Role.ADULT, Role.TEEN, Role.CHILD, Role.GUEST},
    "play_music": {Role.PARENT, Role.ADULT, Role.TEEN, Role.CHILD, Role.GUEST},
    "general_info": {Role.PARENT, Role.ADULT, Role.TEEN, Role.CHILD, Role.GUEST},

    # Tier 2: teen+
    "control_washer": {Role.PARENT, Role.ADULT, Role.TEEN},

    # Tier 3: adult+
    "control_ac": {Role.PARENT, Role.ADULT},
    "control_tv": {Role.PARENT, Role.ADULT},
    "control_geyser": {Role.PARENT, Role.ADULT},
    "control_pump": {Role.PARENT, Role.ADULT},
    "make_calls": {Role.PARENT, Role.ADULT},

    # Special: memory writes (everyone except child)
    "memory_write": {Role.PARENT, Role.ADULT, Role.TEEN, Role.GUEST},

    # Admin
    "admin": {Role.PARENT},
}

# Maps device names → required permission
_DEVICE_PERMISSION_MAP: dict[str, str] = {
    "light": "control_lights",
    "lamp": "control_lights",
    "fan": "control_fan",
    "ac": "control_ac",
    "tv": "control_tv",
    "television": "control_tv",
    "geyser": "control_geyser",
    "heater": "control_geyser",
    "pump": "control_pump",
    "washer": "control_washer",
    "washing machine": "control_washer",
}

_POLITE_DENIALS: dict[str, str] = {
    "control_geyser": "Sorry, only adults can control the geyser for safety reasons.",
    "control_pump": "Sorry, the water pump can only be controlled by adults.",
    "control_ac": "Sorry, you need to ask an adult to change the AC settings.",
    "control_tv": "Sorry, you need to ask an adult to control the TV.",
    "control_washer": "Sorry, the washing machine is for teens and adults only.",
    "make_calls": "Sorry, only adults can make calls.",
    "memory_write": "Sorry, you don't have permission to save memories.",
    "admin": "Sorry, that requires parent permissions.",
}

_DEFAULT_DENIAL = "Sorry, you don't have permission to do that."


class ACL:
    """Access control layer for FamilyRobot."""

    def check_permission(
        self,
        user: FamilyMember,
        permission: str,
    ) -> ACLResult:
        """Check whether *user* has *permission*.

        Returns an ``ACLResult`` with allowed=True/False and a spoken
        denial message when denied.
        """
        allowed_roles = _PERMISSION_MATRIX.get(permission)

        if allowed_roles is None:
            # Unknown permission → allow by default (fail-open for unknown skills)
            logger.warning("Unknown permission '%s'; allowing by default.", permission)
            return ACLResult(allowed=True)

        if user.role in allowed_roles:
            logger.debug("ACL ALLOW: %s (%s) → %s", user.name, user.role.value, permission)
            return ACLResult(allowed=True)

        denial = _POLITE_DENIALS.get(permission, _DEFAULT_DENIAL)
        logger.info(
            "ACL DENY: %s (%s) → %s", user.name, user.role.value, permission
        )
        return ACLResult(
            allowed=False,
            reason=f"Role '{user.role.value}' lacks '{permission}'",
            spoken_denial=denial,
        )

    def check_device(
        self,
        user: FamilyMember,
        device_name: str,
    ) -> ACLResult:
        """Convenience: look up the permission for *device_name* and check."""
        perm = _DEVICE_PERMISSION_MAP.get(device_name.lower(), "general_info")
        return self.check_permission(user, perm)

    def check_intent(
        self,
        user: FamilyMember,
        intent_name: str,
        entities: Optional[dict] = None,
    ) -> ACLResult:
        """Check ACL based on intent name and entities.

        For ``home_control`` intents, checks each device in entities.
        For ``memory_store``, checks ``memory_write`` permission.
        Other intents are allowed by default.
        """
        if intent_name == "home_control" and entities:
            devices = entities.get("devices", [])
            for dev in devices:
                result = self.check_device(user, dev)
                if not result.allowed:
                    return result

        if intent_name == "memory_store":
            return self.check_permission(user, "memory_write")

        return ACLResult(allowed=True)
