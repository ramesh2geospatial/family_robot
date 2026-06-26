"""
Voice Activity Detection package using Silero VAD.
"""

import logging
from typing import Optional

import numpy as np
import silero_vad

logger = logging.getLogger(__name__)


class VoiceActivityDetector:
    def __init__(
        self,
        threshold: float = 0.5,
        sampling_rate: int = 16000,
        min_silence_duration_ms: int = 250,
        speech_pad_ms: int = 30,
    ) -> None:
        self.threshold = threshold
        self.sampling_rate = sampling_rate

        # Load the pre-trained Silero VAD model
        self.model = silero_vad.load_silero_vad()

        # Initialize the VADIterator
        self.iterator = silero_vad.VADIterator(
            model=self.model,
            threshold=threshold,
            sampling_rate=sampling_rate,
            min_silence_duration_ms=min_silence_duration_ms,
            speech_pad_ms=speech_pad_ms,
        )

        self._buffer = b""
        # 512 samples * 2 bytes/sample = 1024 bytes
        self._chunk_size_bytes = 1024

        logger.info("VoiceActivityDetector initialized successfully.")

    def reset(self) -> None:
        """Reset VAD iterator states and internal buffer."""
        self.iterator.reset_states()
        self._buffer = b""

    def process_chunk(self, audio_chunk: bytes) -> Optional[dict]:
        """
        Process incoming audio chunk of arbitrary size.
        Returns a dict indicating speech state transition:
        - {'start': sample_index} when speech starts
        - {'end': sample_index} when speech ends
        - None otherwise
        """
        self._buffer += audio_chunk
        event = None

        while len(self._buffer) >= self._chunk_size_bytes:
            # Slices exactly 512 samples (1024 bytes)
            raw_chunk = self._buffer[: self._chunk_size_bytes]
            self._buffer = self._buffer[self._chunk_size_bytes :]

            # Convert to float32 normalized array
            audio_np = (
                np.frombuffer(raw_chunk, dtype=np.int16).astype(np.float32) / 32768.0
            )

            # Run Silero VAD iterator step
            res = self.iterator(audio_np)
            if res:
                # Capture the start or end event
                event = res

        return event
