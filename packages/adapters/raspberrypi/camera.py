"""
Raspberry Pi camera adapter using Picamera2.
Uses dynamic imports to prevent execution failures on Desktop or Android.
"""

import asyncio
import logging
from typing import Any

import cv2
import numpy as np

from packages.core.ports.camera import CameraPort

logger = logging.getLogger(__name__)


class PiCameraAdapter(CameraPort):
    """
    Camera adapter for Raspberry Pi Camera Module using picamera2.
    """

    def __init__(self, width: int = 640, height: int = 480) -> None:
        self.width = width
        self.height = height
        self._picam: Any = None
        self._is_open = False

    async def open(self, samplerate: int = 16000) -> None:
        """Open the camera interface."""
        try:
            from picamera2 import Picamera2

            # Instantiate picamera2
            self._picam = Picamera2()
            config = self._picam.create_still_configuration(
                main={"size": (self.width, self.height)}
            )
            self._picam.configure(config)
            self._picam.start()
            self._is_open = True
            logger.info(
                f"Pi Camera initialized successfully with resolution "
                f"{self.width}x{self.height}."
            )
        except ImportError:
            logger.warning(
                "picamera2 is not installed; camera capture will fall back to mock."
            )
            self._is_open = True
        except Exception as e:
            logger.error(f"Failed to open Pi Camera: {e}")
            raise RuntimeError(f"Failed to open Pi Camera: {e}")

    async def capture(self) -> Any:
        """
        Capture a single frame.
        Returns a BGR numpy ndarray or None if capture fails.
        """
        if not self._is_open:
            raise RuntimeError("Camera not open. Call open() first.")

        if self._picam:
            try:
                # picamera2 capture_array is synchronous, run in executor
                rgb_frame = await asyncio.to_thread(self._picam.capture_array)
                # Convert RGB to BGR for OpenCV compatibility
                bgr_frame = cv2.cvtColor(rgb_frame, cv2.COLOR_RGB2BGR)
                return bgr_frame
            except Exception as e:
                logger.error(f"Failed to capture frame from picamera2: {e}")
                return None
        else:
            # Fallback mock frame
            return np.zeros((self.height, self.width, 3), dtype=np.uint8)

    async def close(self) -> None:
        """Close the camera interface."""
        if self._picam:
            try:
                self._picam.stop()
            except Exception as e:
                logger.warning(f"Error stopping picamera2: {e}")
            self._picam = None
        self._is_open = False
        logger.info("Pi Camera closed.")
