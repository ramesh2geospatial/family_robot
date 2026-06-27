# Behavioral Contracts

This document records the strict behavioral interfaces and contracts that every adapter and package must satisfy.

## 1. PowerPort Adapter Interface
- **Method**: `battery_pct() -> Optional[int]`
  - Must return battery charge percentage (0-100) or `None` if running on mains.
- **Method**: `on_low_power(cb: Callable[[], Any])`
  - Must spawn a background monitor and execute `cb` if the battery percentage falls below 15% while discharging.

## 2. HomePort Adapter Interface
- **Method**: `set_switch(device_id: str, on: bool) -> bool`
  - Must toggle device state and return success status (`True`/`False`).
- **Method**: `set_level(device_id: str, level: int) -> bool`
  - Must set dimmer level (0-100) and return success status.
- **Method**: `get_state(device_id: str) -> dict`
  - Must return current status dictionary (e.g., `{"on": True, "level": 50}`).

## 3. AudioPort Adapter Interface
- **Method**: `open_input(samplerate: int)`
  - Must open audio stream.
- **Method**: `read_frame() -> bytes`
  - Must return exactly 64ms of mono PCM audio.
