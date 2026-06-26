"""
Desktop audio adapter using PyAudio.
"""

import asyncio
from typing import Optional
import pyaudio

from packages.core.ports.audio import AudioPort


class PyAudioAdapter(AudioPort):
    def __init__(self) -> None:
        self._pa: Optional[pyaudio.PyAudio] = None
        self._input_stream: Optional[pyaudio.Stream] = None
        self._output_stream: Optional[pyaudio.Stream] = None
        self._samplerate: int = 16000

    async def open_input(self, samplerate: int = 16000) -> None:
        """Open audio input stream."""
        if self._pa is None:
            self._pa = pyaudio.PyAudio()
        self._samplerate = samplerate
        
        def _open():
            return self._pa.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=self._samplerate,
                input=True,
                frames_per_buffer=1600,  # 100ms frames
            )
        
        self._input_stream = await asyncio.to_thread(_open)

    async def read_frame(self) -> bytes:
        """Read a single frame of 16-bit PCM mono audio."""
        if not self._input_stream:
            raise RuntimeError("Input stream not open. Call open_input first.")

        def _read():
            # read 100ms of audio (1600 frames at 16000Hz)
            # Use exception_on_overflow=False to avoid issues on slower systems
            return self._input_stream.read(1600, exception_on_overflow=False)

        return await asyncio.to_thread(_read)

    async def play(self, pcm: bytes, samplerate: int) -> None:
        """Play PCM audio data."""
        if self._pa is None:
            self._pa = pyaudio.PyAudio()

        def _play():
            stream = self._pa.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=samplerate,
                output=True,
            )
            try:
                stream.write(pcm)
            finally:
                stream.stop_stream()
                stream.close()

        await asyncio.to_thread(_play)

    async def close(self) -> None:
        """Close audio streams."""
        def _close():
            if self._input_stream:
                try:
                    self._input_stream.stop_stream()
                    self._input_stream.close()
                except Exception:
                    pass
                self._input_stream = None
            if self._pa:
                try:
                    self._pa.terminate()
                except Exception:
                    pass
                self._pa = None

        await asyncio.to_thread(_close)
