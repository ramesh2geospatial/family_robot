"""
Contract tests for NotifyPort adapters.
"""

import pytest

from apps.familyrobot.wiring import MockNotifyAdapter
from packages.adapters.desktop.notify import DesktopNotifyAdapter
from packages.core.ports.notify import NotifyPort


@pytest.mark.contract
@pytest.mark.asyncio
@pytest.mark.parametrize("adapter_cls", [DesktopNotifyAdapter, MockNotifyAdapter])
async def test_notify_adapter_contract(adapter_cls):
    """Verify that all NotifyPort adapters satisfy the contract."""
    adapter: NotifyPort = adapter_cls()
    assert isinstance(adapter, NotifyPort)

    # Test pushing a notification does not throw exceptions
    # (Since push is fire-and-forget/logging or API push)
    await adapter.push(user_id="user_123", title="Test Title", body="Test Body")
