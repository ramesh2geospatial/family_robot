"""
pytest configuration and shared fixtures for FamilyRobot testing.
"""

# Configure any global fixtures here if needed
import sys
from unittest.mock import MagicMock

# Dynamic mocks for missing hardware/ML libraries to ensure tests can collect and run.
MOCK_MODULES = [
    "pyaudio",
    "cv2",
    "faster_whisper",
    "openwakeword",
    "openwakeword.model",
    "silero_vad",
]

for name in MOCK_MODULES:
    try:
        __import__(name)
    except ImportError:
        mock_mod = MagicMock()
        sys.modules[name] = mock_mod
        if name == "openwakeword.model" and "openwakeword" in sys.modules:
            sys.modules["openwakeword"].model = mock_mod


