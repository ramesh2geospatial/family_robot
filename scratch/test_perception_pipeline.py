"""
Verification script for Step 4 (Perception Pipeline).
This script wires PyAudioAdapter to WakeWordDetector, VAD, and STT.
"""

import asyncio
import sys

from packages.adapters.desktop.audio import PyAudioAdapter
from packages.core.perception import (
    SpeechToText,
    VoiceActivityDetector,
    WakeWordDetector,
)


async def main():
    print("Initializing perception pipeline...")
    audio = PyAudioAdapter()

    # We will use 'alexa' as the active wake word name (fallback) since it is built-in.
    detector = WakeWordDetector(wake_word="Hello Puppy")
    vad = VoiceActivityDetector(min_silence_duration_ms=500)
    stt = SpeechToText()

    print("\n--- Perception Pipeline Ready ---")
    print(f"Active wake word detector: {detector.model_name.upper()}")
    print("Opening input stream... speak now (or play an audio cue)...")

    try:
        await audio.open_input(samplerate=16000)
    except Exception as e:
        print(f"Error opening audio input: {e}")
        print(
            "Note: If no audio device is found, please verify your sound card settings."
        )
        return 1

    print("Running wake word detection. Say 'Alexa' (or the configured wake word)...")

    try:
        # State tracking
        is_listening = False
        speech_buffer = []

        while True:
            # Read 100ms (1600 samples = 3200 bytes) of audio
            frame = await audio.read_frame()
            if not frame:
                continue

            if not is_listening:
                # Run wake word detection
                score = detector.predict(frame)
                if score > 0.4:
                    print(f"\n>>> Wake word triggered! Score: {score:.2f}")
                    print(">>> Listening to user speech...")
                    is_listening = True
                    vad.reset()
                    speech_buffer = [frame]
            else:
                # Accumulate speech frames
                speech_buffer.append(frame)

                # Check for voice activity
                vad_event = vad.process_chunk(frame)
                if vad_event:
                    if "end" in vad_event:
                        print(">>> Silence detected. Processing speech...")
                        # Run transcription
                        audio_data = b"".join(speech_buffer)
                        print("Transcribing...")
                        text, lang = stt.transcribe(audio_data)
                        print(f"\nTranscription: {text}")
                        print(f"Detected Language: {lang}\n")

                        # Reset pipeline for next wake word
                        is_listening = False
                        speech_buffer = []
                        print("Waiting for wake word again...")

    except KeyboardInterrupt:
        print("\nStopping perception pipeline...")
    finally:
        await audio.close()
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
