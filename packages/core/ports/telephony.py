"""
Abstract telephony port/interface.
"""

from typing import Protocol, runtime_checkable


@runtime_checkable
class TelephonyPort(Protocol):
    """
    Abstract port for telephony and communication capabilities.
    """

    async def make_call(self, phone_number: str) -> bool:
        """Initiate a voice call to the given phone number."""
        ...

    async def open_whatsapp(self, phone_number: str, message: str) -> bool:
        """Open a WhatsApp chat/call with the given number."""
        ...
