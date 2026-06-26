"""
Unit tests for perception components.
"""

from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from packages.core.perception.stt import SpeechToText
from packages.core.perception.vad import VoiceActivityDetector
from packages.core.perception.wakeword import WakeWordDetector


@pytest.mark.unit
def test_wakeword_detector_built_in():
    """Test WakeWordDetector loads default model when custom is missing."""
    with patch("openwakeword.model.Model") as mock_model_cls:
        mock_model = MagicMock()
        mock_model.predict.return_value = {"alexa": 0.85}
        mock_model_cls.return_value = mock_model

        detector = WakeWordDetector(wake_word="Hello Puppy")
        assert detector.model_name == "alexa"

        # Test predict converts bytes and calls model
        dummy_chunk = b"\x00" * 3200
        score = detector.predict(dummy_chunk)

        assert score == 0.85
        mock_model.predict.assert_called_once()
        # Verify that numpy array was passed to predict
        arg = mock_model.predict.call_args[0][0]
        assert isinstance(arg, np.ndarray)
        assert arg.dtype == np.int16


@pytest.mark.unit
def test_wakeword_detector_custom_exists(tmp_path):
    """Test WakeWordDetector loads custom model if file exists."""
    custom_model = tmp_path / "hello_puppy.onnx"
    custom_model.write_text("fake_onnx_weights", encoding="utf-8")

    with patch("openwakeword.model.Model") as mock_model_cls:
        mock_model = MagicMock()
        mock_model_cls.return_value = mock_model

        detector = WakeWordDetector(
            wake_word="Hello Puppy", model_path=str(custom_model)
        )
        assert detector.model_name == "hello_puppy"


@pytest.mark.unit
def test_vad_detector():
    """Test VoiceActivityDetector processes chunks and wraps VADIterator."""
    with (
        patch("silero_vad.load_silero_vad") as mock_load,
        patch("silero_vad.VADIterator") as mock_iterator_cls,
    ):
        mock_model = MagicMock()
        mock_load.return_value = mock_model

        mock_iterator = MagicMock()
        mock_iterator.return_value = None
        mock_iterator_cls.return_value = mock_iterator

        vad = VoiceActivityDetector()
        assert vad.model == mock_model

        # Test processing chunk of size 1024 bytes (512 samples)
        # It should slice it and run VADIterator once
        chunk = b"\x00" * 1024
        res = vad.process_chunk(chunk)

        assert res is None
        mock_iterator.assert_called_once()

        # Verify reset
        vad.reset()
        mock_iterator.reset_states.assert_called_once()


@pytest.mark.unit
def test_stt_transcribe():
    """Test SpeechToText model loads and transcribes."""
    with patch("packages.core.perception.stt.WhisperModel") as mock_whisper_cls:
        mock_whisper = MagicMock()

        # Mock transcription segments and info
        mock_segment = MagicMock()
        mock_segment.text = "hello world"

        mock_info = MagicMock()
        mock_info.language = "en"

        mock_whisper.transcribe.return_value = ([mock_segment], mock_info)
        mock_whisper_cls.return_value = mock_whisper

        stt = SpeechToText()
        text, lang = stt.transcribe(b"\x00" * 3200)

        assert text == "hello world"
        assert lang == "en"
        mock_whisper.transcribe.assert_called_once()


@pytest.mark.unit
def test_wakeword_detector_empty_and_exception():
    """Test WakeWordDetector returns 0.0 on empty input or error."""
    with patch("openwakeword.model.Model") as mock_model_cls:
        mock_model = MagicMock()
        mock_model.predict.side_effect = Exception("Prediction error")
        mock_model_cls.return_value = mock_model

        detector = WakeWordDetector(wake_word="Hello Puppy")

        # Empty chunk should return 0.0 directly
        assert detector.predict(b"") == 0.0

        # Exception from model should be handled gracefully and return 0.0
        assert detector.predict(b"\x00" * 3200) == 0.0


@pytest.mark.unit
def test_stt_transcribe_exception():
    """Test SpeechToText returns empty strings on exception."""
    with patch("packages.core.perception.stt.WhisperModel") as mock_whisper_cls:
        mock_whisper = MagicMock()
        mock_whisper.transcribe.side_effect = Exception("Model run error")
        mock_whisper_cls.return_value = mock_whisper

        stt = SpeechToText()
        text, lang = stt.transcribe(b"\x00" * 3200)

        assert text == ""
        assert lang == ""


@pytest.mark.unit
def test_vad_detector_events():
    """Test VoiceActivityDetector returning speech start/end events."""
    with (
        patch("silero_vad.load_silero_vad") as mock_load,
        patch("silero_vad.VADIterator") as mock_iterator_cls,
    ):
        mock_model = MagicMock()
        mock_load.return_value = mock_model

        mock_iterator = MagicMock()
        # Return a speech start event on first chunk call
        mock_iterator.return_value = {"start": 16000}
        mock_iterator_cls.return_value = mock_iterator

        vad = VoiceActivityDetector()
        res = vad.process_chunk(b"\x00" * 1024)
        assert res == {"start": 16000}

