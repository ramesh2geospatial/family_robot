"""
Contract tests for AudioPort adapters.
"""

from unittest.mock import MagicMock, patch

import pytest

from apps.familyrobot.wiring import MockAudioAdapter
from packages.adapters.desktop.audio import PyAudioAdapter
from packages.core.ports.audio import AudioPort


@pytest.mark.contract
@pytest.mark.asyncio
async def test_mock_audio_adapter_contract():
    """Verify MockAudioAdapter satisfies the AudioPort contract."""
    adapter: AudioPort = MockAudioAdapter()
    assert isinstance(adapter, AudioPort)

    await adapter.open_input(16000)
    frame = await adapter.read_frame()
    assert isinstance(frame, bytes)
    assert len(frame) == 3200  # 1600 samples * 2 bytes/sample = 3200 bytes
    await adapter.play(frame, 16000)
    await adapter.close()


@pytest.mark.contract
@pytest.mark.asyncio
async def test_pyaudio_adapter_contract():
    """Verify PyAudioAdapter satisfies the AudioPort contract using mocks."""
    with patch("pyaudio.PyAudio") as mock_pa_cls:
        mock_pa = MagicMock()
        mock_stream = MagicMock()
        mock_stream.read.return_value = b"\x00" * 3200
        mock_pa.open.return_value = mock_stream
        mock_pa_cls.return_value = mock_pa

        adapter: AudioPort = PyAudioAdapter()
        assert isinstance(adapter, AudioPort)

        await adapter.open_input(16000)
        # Verify PyAudio is initialized and stream opened
        mock_pa_cls.assert_called_once()
        mock_pa.open.assert_called_once()

        frame = await adapter.read_frame()
        assert isinstance(frame, bytes)
        assert len(frame) == 3200
        mock_stream.read.assert_called_once_with(1600, exception_on_overflow=False)

        # Test play opens and writes to output stream
        await adapter.play(b"\x00" * 3200, 16000)
        assert mock_pa.open.call_count == 2

        await adapter.close()
        assert mock_stream.stop_stream.call_count == 2
        assert mock_stream.close.call_count == 2
        mock_pa.terminate.assert_called_once()
