"""
Perception package containing WakeWord, VAD, and STT components.
"""

from packages.core.perception.stt import SpeechToText
from packages.core.perception.vad import VoiceActivityDetector
from packages.core.perception.wakeword import WakeWordDetector

__all__ = [
    "WakeWordDetector",
    "VoiceActivityDetector",
    "SpeechToText",
]
