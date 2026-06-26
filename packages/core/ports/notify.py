"""
Abstract notification port interface.
"""

from typing import Protocol, runtime_checkable


@runtime_checkable
class NotifyPort(Protocol):
    async def push(self, user_id: str, title: str, body: str) -> None:
        """Push a notification to a specific user."""
        ...
