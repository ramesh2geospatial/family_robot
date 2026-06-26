"""
Termux audio adapter for Android, extending PyAudioAdapter with PulseAudio setup
and CLI fallback playback utilities.
"""

import asyncio
import logging
import os
import shutil
import subprocess
import tempfile
import wave

from packages.adapters.desktop.audio import PyAudioAdapter

logger = logging.getLogger(__name__)


class TermuxAudioAdapter(PyAudioAdapter):
    """
    Audio adapter for Android Termux.
    Inherits from PyAudioAdapter to reuse its PortAudio stream reading/writing.
    If direct PortAudio fails, falls back to Termux API audio utilities.
    """

    async def open_input(self, samplerate: int = 16000) -> None:
        """Open audio input stream, initializing PulseAudio on Termux first."""
        # Try to start PulseAudio daemon if pulseaudio is installed
        if shutil.which("pulseaudio"):
            try:
                # Start pulseaudio daemon
                subprocess.run(
                    ["pulseaudio", "--start", "--exit-idle-time=-1"],
                    capture_output=True,
                    check=False,
                )
                # Load sles source for Android audio integration
                subprocess.run(
                    ["pactl", "load-module", "module-sles-source"],
                    capture_output=True,
                    check=False,
                )
                logger.info("PulseAudio server started and sles-source loaded.")
            except Exception as e:
                logger.warning(f"Could not start PulseAudio server: {e}")

        try:
            await super().open_input(samplerate)
        except Exception as e:
            logger.error(f"PyAudio open_input failed, audio input might fail: {e}")
            raise

    async def play(self, pcm: bytes, samplerate: int) -> None:
        """Play PCM audio data, with fallbacks to CLI players if PyAudio fails."""
        try:
            await super().play(pcm, samplerate)
        except Exception as e:
            logger.warning(
                "Standard PyAudio playback failed, falling back to "
                f"Termux binaries: {e}"
            )
            # Create a temporary WAV file from raw PCM data to play via system tools
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                temp_path = f.name
            try:
                # Write standard WAV headers and data
                with wave.open(temp_path, "wb") as wf:
                    wf.setnchannels(1)
                    wf.setsampwidth(2)  # 16-bit
                    wf.setframerate(samplerate)
                    wf.writeframes(pcm)

                # Attempt available players in order
                if shutil.which("play-audio"):
                    await asyncio.to_thread(
                        subprocess.run,
                        ["play-audio", temp_path],
                        check=True,
                        capture_output=True,
                    )
                elif shutil.which("termux-media-player"):
                    await asyncio.to_thread(
                        subprocess.run,
                        ["termux-media-player", "play", temp_path],
                        check=True,
                        capture_output=True,
                    )
                elif shutil.which("mpv"):
                    await asyncio.to_thread(
                        subprocess.run,
                        ["mpv", "--no-video", temp_path],
                        check=True,
                        capture_output=True,
                    )
                else:
                    logger.error(
                        "No playback tool found (play-audio, termux-media-player, mpv)"
                    )
            except Exception as ex:
                logger.error(f"Playback fallback failed: {ex}")
            finally:
                try:
                    os.unlink(temp_path)
                except Exception:
                    pass
