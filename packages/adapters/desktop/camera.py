"""
Desktop camera adapter using OpenCV.
"""

import asyncio
from typing import Any, Optional

import cv2

from packages.core.ports.camera import CameraPort


class OpenCVCameraAdapter(CameraPort):
    def __init__(self, device_index: int = 0) -> None:
        self.device_index = device_index
        self._cap: Optional[cv2.VideoCapture] = None

    async def open(self, samplerate: int = 16000) -> None:
        """Open the camera interface."""

        def _open():
            cap = cv2.VideoCapture(self.device_index)
            if not cap.isOpened():
                raise RuntimeError(f"Failed to open camera index {self.device_index}")
            return cap

        self._cap = await asyncio.to_thread(_open)

    async def capture(self) -> Any:
        """Capture a single frame from the camera. Returns BGR numpy.ndarray or None."""
        if not self._cap:
            raise RuntimeError("Camera not open. Call open first.")

        def _capture():
            ret, frame = self._cap.read()
            if not ret:
                return None
            return frame

        return await asyncio.to_thread(_capture)

    async def close(self) -> None:
        """Close the camera interface."""

        def _close():
            if self._cap:
                self._cap.release()
                self._cap = None

        await asyncio.to_thread(_close)
