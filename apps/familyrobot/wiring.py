"""
Dynamic components wiring system based on selected platform.
"""

from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional

from packages.core.config import AppConfig
from packages.core.ports.audio import AudioPort
from packages.core.ports.camera import CameraPort
from packages.core.ports.home import HomePort
from packages.core.ports.notify import NotifyPort
from packages.core.ports.power import PowerPort


class MockAudioAdapter(AudioPort):
    async def open_input(self, samplerate: int = 16000) -> None:
        pass

    async def read_frame(self) -> bytes:
        return b"\x00" * 3200  # 100ms of silence at 16kHz 16-bit mono

    async def play(self, pcm: bytes, samplerate: int) -> None:
        pass

    async def close(self) -> None:
        pass


class MockCameraAdapter(CameraPort):
    async def open(self, samplerate: int = 16000) -> None:
        pass

    async def capture(self) -> Any:
        return None

    async def close(self) -> None:
        pass


class MockHomeAdapter(HomePort):
    def __init__(self) -> None:
        self.states: Dict[str, Any] = {}

    async def set_switch(self, device_id: str, on: bool) -> bool:
        self.states[device_id] = {"on": on}
        return True

    async def set_level(self, device_id: str, pct: int) -> bool:
        self.states[device_id] = {"pct": pct}
        return True

    async def send_ir(self, device_id: str, command: str) -> bool:
        return True

    async def get_state(self, device_id: str) -> Dict[str, Any]:
        return self.states.get(device_id, {})


class MockPowerAdapter(PowerPort):
    async def battery_pct(self) -> Optional[int]:
        return 100

    async def on_low_power(self, cb: Callable[[], Any]) -> None:
        pass


class MockNotifyAdapter(NotifyPort):
    async def push(self, user_id: str, title: str, body: str) -> None:
        pass


@dataclass
class WiredComponents:
    audio: AudioPort
    camera: CameraPort
    home: HomePort
    power: PowerPort
    notify: NotifyPort


def wire_components(config: AppConfig) -> WiredComponents:
    """Wire and return components based on platform configuration."""
    if config.platform == "desktop":
        from packages.adapters.desktop import (
            DesktopHomeAdapter,
            DesktopNotifyAdapter,
            DesktopPowerAdapter,
            OpenCVCameraAdapter,
            PyAudioAdapter,
        )
        return WiredComponents(
            audio=PyAudioAdapter(),
            camera=OpenCVCameraAdapter(),
            home=DesktopHomeAdapter(),
            power=DesktopPowerAdapter(),
            notify=DesktopNotifyAdapter(),
        )

    # Fallback to mocks for unsupported / pending platforms
    return WiredComponents(
        audio=MockAudioAdapter(),
        camera=MockCameraAdapter(),
        home=MockHomeAdapter(),
        power=MockPowerAdapter(),
        notify=MockNotifyAdapter(),
    )
