"""
Abstract audio port interface.
"""

from typing import Protocol, runtime_checkable


@runtime_checkable
class AudioPort(Protocol):
    async def open_input(self, samplerate: int = 16000) -> None:
        """Open audio input stream."""
        ...

    async def read_frame(self) -> bytes:
        """Read a single frame of 16-bit PCM mono audio."""
        ...

    async def play(self, pcm: bytes, samplerate: int) -> None:
        """Play PCM audio data."""
        ...

    async def close(self) -> None:
        """Close audio streams."""
        ...
