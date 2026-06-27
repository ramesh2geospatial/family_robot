"""
Contract and unit tests for Raspberry Pi adapters.
"""

import asyncio
import sys
from unittest.mock import MagicMock, patch

import numpy as np
import pyaudio
import pytest

from packages.adapters.raspberrypi import (
    AlsaAudioAdapter,
    PiCameraAdapter,
    PiHomeAdapter,
    PiNotifyAdapter,
    PiPowerAdapter,
)
from packages.core.config import AppConfig, SmartDeviceConfig
from packages.core.ports.audio import AudioPort
from packages.core.ports.camera import CameraPort
from packages.core.ports.home import HomePort
from packages.core.ports.notify import NotifyPort
from packages.core.ports.power import PowerPort


@pytest.mark.contract
@pytest.mark.asyncio
async def test_alsa_audio_adapter_contract():
    """Verify AlsaAudioAdapter satisfies AudioPort and scans for ReSpeaker index."""
    with patch("pyaudio.PyAudio") as mock_pa_cls:
        mock_pa = MagicMock()
        mock_stream = MagicMock()
        mock_stream.read.return_value = b"\x00" * 3200
        mock_pa.open.return_value = mock_stream
        mock_pa_cls.return_value = mock_pa

        # Mock device listing: index 2 is ReSpeaker
        mock_pa.get_device_count.return_value = 3
        mock_pa.get_device_info_by_index.side_effect = lambda idx: {
            0: {"name": "Built-in Audio"},
            1: {"name": "USB Headset"},
            2: {"name": "seeed-2mic-voicecard"},
        }[idx]

        adapter: AudioPort = AlsaAudioAdapter()
        assert isinstance(adapter, AudioPort)

        await adapter.open_input(16000)
        # Should have found index 2 for seeed/respeaker
        assert adapter._input_device_index == 2

        # Verify stream open was called with input_device_index=2
        mock_pa.open.assert_called_with(
            format=pyaudio.paInt16,
            channels=1,
            rate=16000,
            input=True,
            input_device_index=2,
            frames_per_buffer=1600,
        )

        frame = await adapter.read_frame()
        assert isinstance(frame, bytes)
        assert len(frame) == 3200

        await adapter.close()


@pytest.mark.contract
@pytest.mark.asyncio
async def test_pi_camera_adapter_contract():
    """Verify PiCameraAdapter satisfies CameraPort and uses picamera2 properly."""
    # Mock picamera2 module
    mock_picam_mod = MagicMock()
    mock_picam_inst = MagicMock()
    mock_picam_mod.Picamera2.return_value = mock_picam_inst

    # Mock capture array to return a dummy RGB numpy frame (640x480)
    mock_picam_inst.capture_array.return_value = np.zeros((480, 640, 3), dtype=np.uint8)

    sys.modules["picamera2"] = mock_picam_mod

    try:
        adapter: CameraPort = PiCameraAdapter(640, 480)
        assert isinstance(adapter, CameraPort)

        await adapter.open()
        frame = await adapter.capture()

        assert isinstance(frame, np.ndarray)
        assert frame.shape == (480, 640, 3)

        await adapter.close()
        mock_picam_inst.stop.assert_called_once()
    finally:
        sys.modules.pop("picamera2", None)


@pytest.mark.contract
@pytest.mark.asyncio
async def test_pi_camera_adapter_fallback():
    """Verify PiCameraAdapter falls back to mock frame when picamera2 is missing."""
    # Ensure picamera2 is not in sys.modules
    sys.modules.pop("picamera2", None)

    adapter = PiCameraAdapter(640, 480)
    await adapter.open()
    frame = await adapter.capture()

    assert isinstance(frame, np.ndarray)
    assert frame.shape == (480, 640, 3)
    # Mock frame is all zeros
    assert np.all(frame == 0)

    await adapter.close()


@pytest.mark.contract
@pytest.mark.asyncio
async def test_pi_home_adapter_contract():
    """Verify PiHomeAdapter satisfies HomePort and toggles lgpio pin."""
    mock_lgpio = MagicMock()
    mock_lgpio.gpiochip_open.return_value = 42

    sys.modules["lgpio"] = mock_lgpio

    try:
        # Create config with one GPIO relay device and one Kasa device
        config = AppConfig(
            platform="raspberrypi",
            home_devices={
                "geyser": SmartDeviceConfig(type="gpio", address="18"),
                "light": SmartDeviceConfig(type="kasa", address="192.168.1.50"),
            },
        )

        adapter: HomePort = PiHomeAdapter(config)
        assert isinstance(adapter, HomePort)

        # Toggle GPIO relay
        success = await adapter.set_switch("geyser", True)
        assert success is True

        # Verify lgpio operations
        mock_lgpio.gpiochip_open.assert_any_call(4)  # Pi 5 chip
        mock_lgpio.gpio_claim_output.assert_called_with(42, 18)
        mock_lgpio.gpio_write.assert_called_with(42, 18, 1)

        # Toggle off
        success = await adapter.set_switch("geyser", False)
        assert success is True
        mock_lgpio.gpio_write.assert_called_with(42, 18, 0)

        # Cleanup
        await adapter.close()
        mock_lgpio.gpiochip_close.assert_called_with(42)

    finally:
        sys.modules.pop("lgpio", None)


@pytest.mark.contract
@pytest.mark.asyncio
async def test_pi_power_adapter_contract():
    """Verify PiPowerAdapter monitors battery and fires callbacks on low power."""
    mock_smbus = MagicMock()
    mock_bus = MagicMock()
    # Mock register 0x02 to return 12 (critical low battery < 15%)
    mock_bus.read_byte_data.return_value = 12
    mock_smbus.SMBus.return_value = mock_bus

    sys.modules["smbus2"] = mock_smbus

    try:
        adapter: PowerPort = PiPowerAdapter()
        assert isinstance(adapter, PowerPort)

        pct = await adapter.battery_pct()
        assert pct == 12
        mock_bus.read_byte_data.assert_called_with(0x42, 0x02)

        # Test callback loop
        callback_called = asyncio.Event()

        def low_power_cb():
            callback_called.set()

        async def mock_sleep(delay):
            loop = asyncio.get_running_loop()
            fut = loop.create_future()
            loop.call_soon(fut.set_result, None)
            await fut

        # Patch sleep to prevent test hanging, yield control immediately
        with patch(
            "packages.adapters.raspberrypi.power.asyncio.sleep", side_effect=mock_sleep
        ):
            await adapter.on_low_power(low_power_cb)

            # Wait for callback to trigger
            try:
                await asyncio.wait_for(callback_called.wait(), timeout=1.0)
            except asyncio.TimeoutError:
                pytest.fail("Callback was not called within timeout")
            assert callback_called.is_set()

            if adapter._monitor_task:
                adapter._monitor_task.cancel()

    finally:
        sys.modules.pop("smbus2", None)


@pytest.mark.contract
@pytest.mark.asyncio
async def test_pi_notify_adapter_contract():
    """Verify PiNotifyAdapter conforms to NotifyPort."""
    adapter: NotifyPort = PiNotifyAdapter()
    assert isinstance(adapter, NotifyPort)
    # Should execute successfully without throwing errors
    await adapter.push("user1", "Hello", "How is the Pi?")
