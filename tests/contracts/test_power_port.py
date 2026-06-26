"""
Contract tests for PowerPort adapters.
"""

import pytest

from apps.familyrobot.wiring import MockPowerAdapter
from packages.adapters.desktop.power import DesktopPowerAdapter
from packages.core.ports.power import PowerPort


@pytest.mark.contract
@pytest.mark.asyncio
@pytest.mark.parametrize("adapter_cls", [DesktopPowerAdapter, MockPowerAdapter])
async def test_power_adapter_contract(adapter_cls):
    """Verify that all PowerPort adapters satisfy the contract."""
    adapter: PowerPort = adapter_cls()
    assert isinstance(adapter, PowerPort)

    # Test battery percentage returns integer, None, or similar
    pct = await adapter.battery_pct()
    assert pct is None or isinstance(pct, int)
    if isinstance(pct, int):
        assert 0 <= pct <= 100

    # Test registering callback on low power runs without throwing errors
    called = False

    def low_power_cb():
        nonlocal called
        called = True

    await adapter.on_low_power(low_power_cb)
    # Callback is register-only, doesn't need to fire immediately
    assert called is False
