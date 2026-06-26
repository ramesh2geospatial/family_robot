"""
Android/Termux platform adapters package.
"""

from packages.adapters.android.audio import TermuxAudioAdapter
from packages.adapters.android.camera import TermuxCameraAdapter
from packages.adapters.android.home import TermuxHomeAdapter
from packages.adapters.android.notify import TermuxNotifyAdapter
from packages.adapters.android.power import TermuxPowerAdapter

__all__ = [
    "TermuxAudioAdapter",
    "TermuxCameraAdapter",
    "TermuxHomeAdapter",
    "TermuxPowerAdapter",
    "TermuxNotifyAdapter",
]
