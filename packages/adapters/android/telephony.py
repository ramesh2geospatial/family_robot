"""
Termux telephony adapter for Android.
"""

import logging
import shutil
import subprocess
from packages.core.ports.telephony import TelephonyPort

logger = logging.getLogger(__name__)

class TermuxTelephonyAdapter(TelephonyPort):
    """
    Android telephony adapter using Termux API commands.
    """

    async def make_call(self, phone_number: str) -> bool:
        if not shutil.which("termux-telephony-call"):
            logger.info(f"[Telephony Mock] No termux-telephony-call CLI; logging call to {phone_number}")
            return True
        try:
            # Invokes native Android dialer via Termux
            subprocess.run(["termux-telephony-call", phone_number], check=True)
            logger.info(f"Termux telephony call initiated to {phone_number}")
            return True
        except Exception as e:
            logger.error(f"Failed to make Termux call: {e}")
            return False

    async def open_whatsapp(self, phone_number: str, message: str) -> bool:
        url = f"https://api.whatsapp.com/send?phone={phone_number}&text={message}"
        try:
            if shutil.which("termux-open"):
                subprocess.run(["termux-open", url], check=True)
                logger.info(f"Opened WhatsApp link via termux-open: {phone_number}")
                return True
            else:
                logger.info(f"[Telephony Mock] No termux-open; WhatsApp simulation link: {url}")
                return True
        except Exception as e:
            logger.error(f"Failed to open WhatsApp: {e}")
            return False
