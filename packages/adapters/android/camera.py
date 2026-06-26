"""
Termux camera adapter for Android, supporting live URL feeds (IP webcam)
and offline termux-camera-photo snapshots.
"""

import asyncio
import logging
import os
import shutil
import subprocess
import tempfile
import urllib.request
from typing import Any, Optional

from packages.core.ports.camera import CameraPort

logger = logging.getLogger(__name__)


class TermuxCameraAdapter(CameraPort):
    """
    Camera adapter for Android Termux.
    Supports fetching frames from a local IP Camera URL, or executing
    the native termux-camera-photo snapshot command.
    """

    def __init__(self, device_index: int = 0, stream_url: Optional[str] = None) -> None:
        self.device_index = device_index
        self.stream_url = stream_url
        self._is_open = False

    async def open(self, samplerate: int = 16000) -> None:
        """Open the camera interface."""
        self._is_open = True
        logger.info(
            "TermuxCameraAdapter opened (index: %s, stream_url: %s)",
            self.device_index,
            self.stream_url,
        )

    async def capture(self) -> Any:
        """
        Capture a single frame.
        Returns a BGR numpy ndarray or None if capture fails.
        """
        if not self._is_open:
            raise RuntimeError("Camera not open. Call open() first.")

        # Mode 1: Stream URL (IP Webcam feed)
        if self.stream_url:
            try:
                import cv2
                import numpy as np

                # Fetch image bytes via HTTP
                req = urllib.request.Request(self.stream_url)
                # Run in executor to avoid blocking the asyncio event loop
                img_data = await asyncio.to_thread(self._fetch_url, req)
                if img_data:
                    img_arr = np.frombuffer(img_data, dtype=np.uint8)
                    frame = cv2.imdecode(img_arr, cv2.IMREAD_COLOR)
                    return frame
            except Exception as e:
                logger.error(
                    f"Failed to capture frame from stream URL {self.stream_url}: {e}"
                )
                return None

        # Mode 2: Offline native termux-camera-photo snapshot
        if shutil.which("termux-camera-photo"):
            try:
                import cv2

                with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as f:
                    temp_path = f.name
                try:
                    cmd = [
                        "termux-camera-photo",
                        "-c",
                        str(self.device_index),
                        temp_path,
                    ]
                    # Run subprocess in executor
                    res = await asyncio.to_thread(
                        subprocess.run, cmd, capture_output=True, text=True
                    )
                    if res.returncode != 0:
                        logger.warning(f"termux-camera-photo failed: {res.stderr}")
                        return None

                    if os.path.exists(temp_path) and os.path.getsize(temp_path) > 0:
                        frame = cv2.imread(temp_path)
                        return frame
                finally:
                    try:
                        os.unlink(temp_path)
                    except Exception:
                        pass
            except Exception as e:
                logger.error(f"Failed to capture photo via termux-camera-photo: {e}")
                return None

        # Fallback/mock for non-termux local dev testing
        logger.info(
            "termux-camera-photo not found and no stream URL set; returning mock frame"
        )
        try:
            import numpy as np

            return np.zeros((480, 640, 3), dtype=np.uint8)
        except ImportError:
            return None

    def _fetch_url(self, req: urllib.request.Request) -> Optional[bytes]:
        try:
            with urllib.request.urlopen(req, timeout=3.0) as response:
                return response.read()
        except Exception as e:
            logger.error(f"Error fetching camera URL: {e}")
            return None

    async def close(self) -> None:
        """Close the camera interface."""
        self._is_open = False
        logger.info("TermuxCameraAdapter closed.")
