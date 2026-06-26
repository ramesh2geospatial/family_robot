"""
Desktop notification adapter.
"""

import logging

from packages.core.ports.notify import NotifyPort

logger = logging.getLogger(__name__)


class DesktopNotifyAdapter(NotifyPort):
    async def push(self, user_id: str, title: str, body: str) -> None:
        """Push a notification to a specific user."""
        logger.info("DesktopNotifyAdapter: push to %s | %s: %s", user_id, title, body)
