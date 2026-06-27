"""
Raspberry Pi ALSA audio adapter using PyAudio.
Automatically scans and binds to ReSpeaker HATs if present.
"""

import asyncio
import logging
from typing import Optional

import pyaudio

from packages.adapters.desktop.audio import PyAudioAdapter

logger = logging.getLogger(__name__)


class AlsaAudioAdapter(PyAudioAdapter):
    """
    Audio adapter for Raspberry Pi (ALSA/ReSpeaker).
    Inherits from PyAudioAdapter and automatically binds to ReSpeaker devices if found.
    """

    def __init__(self) -> None:
        super().__init__()
        self._input_device_index: Optional[int] = None
        self._output_device_index: Optional[int] = None

    async def open_input(self, samplerate: int = 16000) -> None:
        """Open audio input stream, scanning for ReSpeaker device index."""
        if self._pa is None:
            self._pa = pyaudio.PyAudio()

        self._samplerate = samplerate

        # Scan for ReSpeaker/seeed hardware HAT
        try:
            device_count = self._pa.get_device_count()
            for i in range(device_count):
                device_info = self._pa.get_device_info_by_index(i)
                name = device_info.get("name", "").lower()
                if "respeaker" in name or "seeed" in name:
                    self._input_device_index = i
                    logger.info(
                        f"Found ReSpeaker hardware input device: "
                        f"'{device_info.get('name')}' at index {i}"
                    )
                    break
        except Exception as e:
            logger.warning(f"Error scanning for ReSpeaker devices: {e}")

        def _open():
            # Use found index if available
            return self._pa.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=self._samplerate,
                input=True,
                input_device_index=self._input_device_index,
                frames_per_buffer=1600,  # 100ms frames
            )

        self._input_stream = await asyncio.to_thread(_open)
        logger.info("Pi ALSA input stream opened successfully.")
