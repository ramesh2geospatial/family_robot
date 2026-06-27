"""
Raspberry Pi notification adapter implementing NotifyPort.
"""

import logging

from packages.core.ports.notify import NotifyPort

logger = logging.getLogger(__name__)


class PiNotifyAdapter(NotifyPort):
    """
    Notification adapter for Raspberry Pi.
    Logs pushes locally (will connect to ntfy / WebPush in Step 14).
    """

    async def push(self, user_id: str, title: str, body: str) -> None:
        """Log the notification push."""
        logger.info(f"[Pi Notify] Push to {user_id}: {title} - {body}")
