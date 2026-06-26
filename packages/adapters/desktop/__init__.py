"""
Desktop platform adapters package.
"""

from packages.adapters.desktop.audio import PyAudioAdapter
from packages.adapters.desktop.camera import OpenCVCameraAdapter
from packages.adapters.desktop.home import DesktopHomeAdapter
from packages.adapters.desktop.power import DesktopPowerAdapter
from packages.adapters.desktop.notify import DesktopNotifyAdapter

__all__ = [
    "PyAudioAdapter",
    "OpenCVCameraAdapter",
    "DesktopHomeAdapter",
    "DesktopPowerAdapter",
    "DesktopNotifyAdapter",
]
