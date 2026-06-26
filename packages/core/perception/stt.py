"""
Speech-to-Text package using faster-whisper.
"""

import logging

import numpy as np
from faster_whisper import WhisperModel

logger = logging.getLogger(__name__)


class SpeechToText:
    def __init__(
        self,
        model_name: str = "small",
        device: str = "cpu",
        compute_type: str = "int8",
    ) -> None:
        self.model_name = model_name
        self.device = device
        self.compute_type = compute_type

        logger.info(
            "Loading Whisper model '%s' on %s (%s)...",
            model_name,
            device,
            compute_type,
        )
        self.model = WhisperModel(
            model_name,
            device=device,
            compute_type=compute_type,
        )
        logger.info("Whisper model '%s' loaded successfully.", model_name)

    def transcribe(self, audio_data: bytes) -> tuple[str, str]:
        """
        Transcribe raw 16-bit PCM audio bytes.
        Returns a tuple of:
        - transcribed text (str)
        - detected language code (str)
        """
        if not audio_data:
            return "", ""

        # Convert raw PCM bytes to normalized float32 numpy array
        audio_np = (
            np.frombuffer(audio_data, dtype=np.int16).astype(np.float32) / 32768.0
        )

        try:
            # Transcribe audio. beam_size=5 is standard
            # model.transcribe accepts 1D float32 numpy array representing the waveform
            segments, info = self.model.transcribe(audio_np, beam_size=5)

            # Iterate over segments and join them
            text_segments = []
            for segment in segments:
                text_segments.append(segment.text)

            transcribed_text = " ".join(text_segments).strip()
            detected_language = info.language
        except Exception as e:
            logger.error("Error transcribing audio with Whisper: %s", e, exc_info=True)
            return "", ""

        logger.info(
            "STT result: lang=%s | text='%s'", detected_language, transcribed_text
        )
        return transcribed_text, detected_language
