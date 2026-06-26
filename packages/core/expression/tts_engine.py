"""
Text-to-speech engine using Piper TTS.

Implements the TTSPort protocol. Falls back to pyttsx3 (system TTS)
if piper is unavailable.
"""

from __future__ import annotations

import asyncio
import io
import logging
import wave
from typing import Optional

logger = logging.getLogger(__name__)


class PiperTTSEngine:
    """Piper-based TTS with pyttsx3 fallback.

    Satisfies the ``TTSPort`` protocol.
    """

    def __init__(
        self,
        model_path: Optional[str] = None,
        config_path: Optional[str] = None,
    ) -> None:
        self._model_path = model_path
        self._config_path = config_path
        self._piper_voice: Optional[object] = None
        self._pyttsx_engine: Optional[object] = None
        self._use_piper: bool = True

    def _init_piper(self) -> None:
        """Try to initialise Piper TTS."""
        try:
            from piper import PiperVoice  # type: ignore[import-untyped]

            if self._model_path:
                self._piper_voice = PiperVoice.load(
                    self._model_path, config_path=self._config_path
                )
                logger.info("Piper TTS loaded from %s", self._model_path)
            else:
                logger.warning("No Piper model_path; falling back to pyttsx3.")
                self._use_piper = False
        except ImportError:
            logger.info("piper-tts not installed; falling back to pyttsx3.")
            self._use_piper = False
        except Exception as exc:
            logger.warning("Piper init failed (%s); falling back to pyttsx3.", exc)
            self._use_piper = False

    def _init_pyttsx(self) -> None:
        """Initialise pyttsx3 fallback."""
        try:
            import pyttsx3  # type: ignore[import-untyped]

            self._pyttsx_engine = pyttsx3.init()
            logger.info("pyttsx3 TTS fallback initialised.")
        except Exception as exc:
            logger.error("pyttsx3 init failed: %s", exc)

    def _synthesize_piper(self, text: str) -> tuple[bytes, int]:
        """Synthesise with Piper and return (PCM bytes, sample_rate)."""
        buf = io.BytesIO()
        with wave.open(buf, "wb") as wav:
            self._piper_voice.synthesize(text, wav)  # type: ignore[union-attr]
        buf.seek(0)
        with wave.open(buf, "rb") as wav:
            sample_rate = wav.getframerate()
            pcm = wav.readframes(wav.getnframes())
        return pcm, sample_rate

    def _synthesize_pyttsx(self, text: str) -> tuple[bytes, int]:
        """Synthesise with pyttsx3 and return (PCM bytes, sample_rate).

        pyttsx3 does not easily return raw PCM, so we save to a temp
        WAV file and read it back.
        """
        import tempfile, os

        tmp_path = os.path.join(tempfile.gettempdir(), "_fr_tts.wav")
        engine = self._pyttsx_engine
        engine.save_to_file(text, tmp_path)  # type: ignore[union-attr]
        engine.runAndWait()  # type: ignore[union-attr]

        try:
            with wave.open(tmp_path, "rb") as wav:
                sample_rate = wav.getframerate()
                pcm = wav.readframes(wav.getnframes())
            return pcm, sample_rate
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    async def synthesize(
        self,
        text: str,
        *,
        lang: str = "en",
        voice: Optional[str] = None,
    ) -> tuple[bytes, int]:
        """Convert *text* to speech.

        Returns ``(pcm_bytes, sample_rate)``.
        Satisfies the ``TTSPort`` protocol.
        """
        if not text or not text.strip():
            # Return 0.5 s of silence at 22050 Hz
            return b"\x00" * 22050, 22050

        # Lazy initialisation
        if self._piper_voice is None and self._use_piper:
            await asyncio.to_thread(self._init_piper)
        if not self._use_piper and self._pyttsx_engine is None:
            await asyncio.to_thread(self._init_pyttsx)

        try:
            if self._use_piper and self._piper_voice is not None:
                return await asyncio.to_thread(self._synthesize_piper, text)
            elif self._pyttsx_engine is not None:
                return await asyncio.to_thread(self._synthesize_pyttsx, text)
            else:
                logger.error("No TTS backend available.")
                return b"\x00" * 22050, 22050
        except Exception as exc:
            logger.error("TTS synthesis failed: %s", exc, exc_info=True)
            return b"\x00" * 22050, 22050
