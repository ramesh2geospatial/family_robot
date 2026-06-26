"""
Termux notification adapter for Android.
Triggers Android system notifications using termux-notification CLI.
"""

import logging
import shutil
import subprocess

from packages.core.ports.notify import NotifyPort

logger = logging.getLogger(__name__)


class TermuxNotifyAdapter(NotifyPort):
    """
    Notification adapter using Android's native Termux API notifications.
    """

    async def push(self, user_id: str, title: str, body: str) -> None:
        """Send a system notification to the Android host."""
        if not shutil.which("termux-notification"):
            logger.info(f"[Notify Mock] Android push to {user_id}: {title} - {body}")
            return

        try:
            cmd = [
                "termux-notification",
                "--title",
                title,
                "--content",
                body,
                "--sound",
            ]
            subprocess.run(cmd, check=True, capture_output=True)
            logger.info(f"Android system notification pushed: {title}")
        except Exception as e:
            logger.error(f"Failed to push notification via termux-notification: {e}")
