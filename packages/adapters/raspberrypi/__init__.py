"""
Raspberry Pi platform adapters package.
"""

from packages.adapters.raspberrypi.audio import AlsaAudioAdapter
from packages.adapters.raspberrypi.camera import PiCameraAdapter
from packages.adapters.raspberrypi.home import PiHomeAdapter
from packages.adapters.raspberrypi.notify import PiNotifyAdapter
from packages.adapters.raspberrypi.power import PiPowerAdapter
from packages.adapters.raspberrypi.telephony import PiTelephonyAdapter

__all__ = [
    "AlsaAudioAdapter",
    "PiCameraAdapter",
    "PiHomeAdapter",
    "PiPowerAdapter",
    "PiNotifyAdapter",
    "PiTelephonyAdapter",
]
