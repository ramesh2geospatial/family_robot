"""
Contract tests for HomePort adapters.
"""

import pytest

from apps.familyrobot.wiring import MockHomeAdapter
from packages.adapters.desktop.home import DesktopHomeAdapter
from packages.core.ports.home import HomePort


@pytest.mark.contract
@pytest.mark.asyncio
@pytest.mark.parametrize("adapter_cls", [DesktopHomeAdapter, MockHomeAdapter])
async def test_home_adapter_contract(adapter_cls):
    """Verify that all HomePort adapters satisfy the contract."""
    adapter: HomePort = adapter_cls()
    assert isinstance(adapter, HomePort)

    # Initial state should be empty or default
    initial_state = await adapter.get_state("device_1")
    assert isinstance(initial_state, dict)

    # Test set_switch updates the state correctly
    res = await adapter.set_switch("device_1", on=True)
    assert res is True
    state = await adapter.get_state("device_1")
    assert state.get("on") is True

    # Test set_level updates the level correctly
    res = await adapter.set_level("device_2", pct=80)
    assert res is True
    state = await adapter.get_state("device_2")
    assert state.get("pct") == 80

    # Test send_ir returns a boolean (e.g. success)
    res = await adapter.send_ir("device_3", command="MUTE")
    assert isinstance(res, bool)
