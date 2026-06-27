"""
Mock telephony adapter for Desktop.
"""

import logging

from packages.core.ports.telephony import TelephonyPort

logger = logging.getLogger(__name__)


class DesktopTelephonyAdapter(TelephonyPort):
    """
    Mock telephony adapter logging calls and messages.
    """

    async def make_call(self, phone_number: str) -> bool:
        logger.info(f"[Telephony Mock] Initiating voice call to {phone_number}")
        return True

    async def open_whatsapp(self, phone_number: str, message: str) -> bool:
        logger.info(
            f"[Telephony Mock] Opening WhatsApp chat with {phone_number}: message='{message}'"
        )
        return True
