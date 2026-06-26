"""
Abstract camera port interface.
"""

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class CameraPort(Protocol):
    async def open(self, samplerate: int = 16000) -> None:
        """Open the camera interface."""
        ...

    async def capture(self) -> Any:
        """Capture a single frame from the camera. Returns BGR numpy.ndarray or None."""
        ...

    async def close(self) -> None:
        """Close the camera interface."""
        ...
