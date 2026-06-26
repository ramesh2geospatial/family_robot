"""
Contract and unit tests for Termux/Android adapters.
"""

import asyncio
import json
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from packages.adapters.android import (
    TermuxAudioAdapter,
    TermuxCameraAdapter,
    TermuxHomeAdapter,
    TermuxNotifyAdapter,
    TermuxPowerAdapter,
)
from packages.core.ports.audio import AudioPort
from packages.core.ports.camera import CameraPort
from packages.core.ports.home import HomePort
from packages.core.ports.notify import NotifyPort
from packages.core.ports.power import PowerPort


@pytest.mark.contract
@pytest.mark.asyncio
async def test_termux_audio_adapter_contract():
    """Verify TermuxAudioAdapter satisfies AudioPort and handles pulseaudio start."""
    with (
        patch("pyaudio.PyAudio") as mock_pa_cls,
        patch("shutil.which") as mock_which,
        patch("subprocess.run") as mock_run,
    ):
        mock_pa = MagicMock()
        mock_stream = MagicMock()
        mock_stream.read.return_value = b"\x00" * 3200
        mock_pa.open.return_value = mock_stream
        mock_pa_cls.return_value = mock_pa

        # Simulate pulseaudio binary exists
        mock_which.side_effect = lambda x: (
            "/usr/bin/pulseaudio" if x == "pulseaudio" else None
        )

        adapter: AudioPort = TermuxAudioAdapter()
        assert isinstance(adapter, AudioPort)

        await adapter.open_input(16000)

        # Assert pulseaudio daemon was started
        mock_run.assert_any_call(
            ["pulseaudio", "--start", "--exit-idle-time=-1"],
            capture_output=True,
            check=False,
        )
        mock_run.assert_any_call(
            ["pactl", "load-module", "module-sles-source"],
            capture_output=True,
            check=False,
        )

        frame = await adapter.read_frame()
        assert isinstance(frame, bytes)
        assert len(frame) == 3200

        # Assert output playback standard works
        await adapter.play(b"\x00" * 3200, 16000)

        await adapter.close()


@pytest.mark.contract
@pytest.mark.asyncio
async def test_termux_audio_adapter_fallback_playback():
    """Verify TermuxAudioAdapter fallback play on pyaudio write failure."""
    with (
        patch("pyaudio.PyAudio") as mock_pa_cls,
        patch("shutil.which") as mock_which,
        patch("subprocess.run") as mock_run,
        patch("wave.open") as mock_wave_open,
    ):
        mock_pa = MagicMock()
        # Make pyaudio stream.write throw an error
        mock_stream = MagicMock()
        mock_stream.write.side_effect = Exception("Audio write failed")
        mock_pa.open.return_value = mock_stream
        mock_pa_cls.return_value = mock_pa

        # Simulate play-audio binary exists
        mock_which.side_effect = lambda x: (
            "/usr/bin/play-audio" if x == "play-audio" else None
        )

        adapter = TermuxAudioAdapter()
        # Test play falls back to play-audio CLI
        await adapter.play(b"\x00" * 3200, 16000)

        # Assert wave file was written and subprocess called with play-audio
        mock_wave_open.assert_called_once()
        from unittest.mock import ANY

        mock_run.assert_called_with(
            ["play-audio", ANY], check=True, capture_output=True
        )


@pytest.mark.contract
@pytest.mark.asyncio
async def test_termux_camera_adapter_contract():
    """Verify TermuxCameraAdapter satisfies CameraPort."""
    adapter: CameraPort = TermuxCameraAdapter(device_index=0)
    assert isinstance(adapter, CameraPort)

    await adapter.open()
    frame = await adapter.capture()
    # In mock/fallback mode, it returns a blank numpy frame or None
    assert frame is None or isinstance(frame, np.ndarray)
    await adapter.close()


@pytest.mark.contract
@pytest.mark.asyncio
async def test_termux_camera_adapter_stream_url():
    """Verify TermuxCameraAdapter stream URL fetches and decodes image bytes."""
    with (
        patch("urllib.request.urlopen") as mock_urlopen,
        patch("cv2.imdecode") as mock_imdecode,
    ):
        mock_response = MagicMock()
        mock_response.read.return_value = b"fake_jpeg_bytes"
        mock_urlopen.return_value.__enter__.return_value = mock_response

        mock_imdecode.return_value = np.zeros((480, 640, 3), dtype=np.uint8)

        adapter = TermuxCameraAdapter(stream_url="http://192.168.1.5:8080/shot.jpg")
        await adapter.open()
        frame = await adapter.capture()

        assert frame is not None
        assert frame.shape == (480, 640, 3)
        mock_imdecode.assert_called_once()
        await adapter.close()


@pytest.mark.contract
@pytest.mark.asyncio
async def test_termux_camera_adapter_native_snapshot():
    """Verify TermuxCameraAdapter uses termux-camera-photo snapshot command."""
    with (
        patch("shutil.which") as mock_which,
        patch("subprocess.run") as mock_run,
        patch("cv2.imread") as mock_imread,
        patch("os.path.exists") as mock_exists,
        patch("os.path.getsize") as mock_getsize,
    ):
        # Simulate termux-camera-photo exists
        mock_which.side_effect = lambda x: (
            "/usr/bin/termux-camera-photo" if x == "termux-camera-photo" else None
        )

        mock_res = MagicMock()
        mock_res.returncode = 0
        mock_run.return_value = mock_res

        mock_exists.return_value = True
        mock_getsize.return_value = 1000
        mock_imread.return_value = np.zeros((480, 640, 3), dtype=np.uint8)

        adapter = TermuxCameraAdapter(device_index=1)
        await adapter.open()
        frame = await adapter.capture()

        assert frame is not None
        mock_run.assert_called_once()
        assert "termux-camera-photo" in mock_run.call_args[0][0]
        assert "-c" in mock_run.call_args[0][0]
        assert "1" in mock_run.call_args[0][0]
        mock_imread.assert_called_once()
        await adapter.close()


@pytest.mark.contract
@pytest.mark.asyncio
async def test_termux_home_adapter_contract():
    """Verify TermuxHomeAdapter satisfies HomePort."""
    adapter: HomePort = TermuxHomeAdapter()
    assert isinstance(adapter, HomePort)

    # Initial state should be empty
    initial_state = await adapter.get_state("device_1")
    assert initial_state == {}

    # Test set_switch updates the state
    res = await adapter.set_switch("device_1", on=True)
    assert res is True
    state = await adapter.get_state("device_1")
    assert state.get("on") is True

    # Test set_level updates level
    res = await adapter.set_level("device_2", pct=50)
    assert res is True
    state = await adapter.get_state("device_2")
    assert state.get("pct") == 50

    # Test send_ir returns a boolean
    res = await adapter.send_ir("device_3", command="MUTE")
    assert isinstance(res, bool)


@pytest.mark.contract
@pytest.mark.asyncio
async def test_termux_notify_adapter_contract():
    """Verify TermuxNotifyAdapter satisfies NotifyPort."""
    with patch("shutil.which") as mock_which, patch("subprocess.run") as mock_run:
        # 1. Native CLI available
        mock_which.side_effect = lambda x: (
            "/usr/bin/termux-notification" if x == "termux-notification" else None
        )

        adapter: NotifyPort = TermuxNotifyAdapter()
        assert isinstance(adapter, NotifyPort)

        await adapter.push("user_1", "Low Battery", "Charge your robot")
        mock_run.assert_called_once_with(
            [
                "termux-notification",
                "--title",
                "Low Battery",
                "--content",
                "Charge your robot",
                "--sound",
            ],
            check=True,
            capture_output=True,
        )


@pytest.mark.contract
@pytest.mark.asyncio
async def test_termux_power_adapter_contract():
    """Verify TermuxPowerAdapter satisfies PowerPort."""
    with patch("shutil.which") as mock_which, patch("subprocess.run") as mock_run:
        # Simulate termux-battery-status exists
        mock_which.side_effect = lambda x: (
            "/usr/bin/termux-battery-status" if x == "termux-battery-status" else None
        )

        mock_res = MagicMock()
        mock_res.stdout = json.dumps(
            {
                "health": "GOOD",
                "percentage": 42,
                "status": "DISCHARGING",
                "temperature": 29.5,
            }
        )
        mock_run.return_value = mock_res

        adapter: PowerPort = TermuxPowerAdapter()
        assert isinstance(adapter, PowerPort)

        pct = await adapter.battery_pct()
        assert pct == 42
        mock_run.assert_called_once_with(
            ["termux-battery-status"], capture_output=True, text=True, check=True
        )


@pytest.mark.contract
@pytest.mark.asyncio
async def test_termux_power_adapter_low_battery_callback():
    """Verify low battery monitor triggers the callback."""
    from unittest.mock import AsyncMock

    with (
        patch("shutil.which") as mock_which,
        patch("subprocess.run") as mock_run,
        patch("packages.adapters.android.power.asyncio.sleep", new_callable=AsyncMock),
    ):
        mock_which.return_value = "/usr/bin/termux-battery-status"

        mock_res = MagicMock()
        mock_res.stdout = json.dumps({"percentage": 10, "status": "DISCHARGING"})
        mock_run.return_value = mock_res

        adapter = TermuxPowerAdapter()
        callback_called = asyncio.Event()

        async def callback():
            callback_called.set()

        # Register callback, which starts monitor task
        await adapter.on_low_power(callback)

        # Wait for the background monitor loop to trigger the callback
        try:
            await asyncio.wait_for(callback_called.wait(), timeout=1.0)
        except asyncio.TimeoutError:
            pytest.fail("Callback was not called within timeout")

        # Clean up the monitor task to prevent background errors after test completes
        if adapter._monitor_task:
            adapter._monitor_task.cancel()
