# FamilyRobot – Architecture Reference (implementation-level)

> Loaded on demand by the `familyrobot-dev` skill. Contains the concrete module layout, port interfaces, and platform adapter contracts needed to implement the system from scratch.

## 1. Monorepo layout (create exactly this)

```
familyrobot/
├── pyproject.toml              # project + optional extras: [desktop],[android],[pi]
├── packages/
│   ├── core/                   # orchestrator, supervisor, event bus, config loader, logging
│   │   ├── ports/              # abstract interfaces ONLY (no impl): audio, camera, home, power, notify
│   │   ├── perception/         # wakeword, vad, stt, speaker_id, face_id (device-agnostic)
│   │   ├── cognition/          # llm_client (local+cloud), memory (sqlite+vector), rag, intent_router
│   │   ├── expression/         # tts, ui_state (ring/face abstraction)
│   │   ├── skills/             # one subpackage per skill (see skills-catalog.md)
│   │   ├── home/               # mqtt client, smart-plug drivers, ir driver (network-based, shared)
│   │   ├── governance/         # identity_fusion, acl, policy, audit_log
│   │   └── webapp/             # FastAPI app + PWA (enroll, control, memory review)
│   │
│   └── adapters/
│       ├── desktop/            # audio=portaudio, camera=opencv, home=mock, power=none
│       ├── android/            # audio=termux, camera=termux/ipcam, home=wifi/esp, power=battery
│       └── raspberrypi/        # audio=alsa/hat, camera=picamera2, home=gpio+wifi, power=ups_hat
│
├── apps/familyrobot/           # entrypoint: load config -> pick adapters -> start core
├── deploy/{docker,android-termux,raspberrypi}/
├── config/{base,desktop,android,raspberrypi}.yaml
├── models/                     # downloaded model files (gitignored)
└── tests/                      # shared tests + per-port contract suites
```

## 2. Port interfaces (the contracts shared code depends on)
Define these as Python `Protocol`/`ABC` classes in `packages/ports/`. Shared code imports ONLY these.

```python
# ports/audio.py
class AudioPort(Protocol):
    async def open_input(self, samplerate: int = 16000) -> None: ...
    async def read_frame(self) -> bytes: ...             # 16-bit PCM mono chunk
    async def play(self, pcm: bytes, samplerate: int) -> None: ...
    async def close(self) -> None: ...

# ports/camera.py
class CameraPort(Protocol):
    async def open(self, samplerate: int = 16000) -> None: ...
    async def capture(self) -> "ndarray | None": ...     # BGR frame or None
    async def close(self) -> None: ...

# ports/home.py -- the device-control abstraction
class HomePort(Protocol):
    async def set_switch(self, device_id: str, on: bool) -> bool: ...
    async def set_level(self, device_id: str, pct: int) -> bool: ...      # dim/fan speed
    async def send_ir(self, device_id: str, command: str) -> bool: ...
    async def get_state(self, device_id: str) -> dict: ...

# ports/power.py
class PowerPort(Protocol):
    async def battery_pct(self) -> int | None: ...       # None if mains-only
    async def on_low_power(self, cb) -> None: ...        # trigger safe shutdown

# ports/notify.py
class NotifyPort(Protocol):
    async def push(self, user_id: str, title: str, body: str) -> None: ...
    ...
```

**Rule:** every adapter implements one or more of these and must pass the matching contract test in `tests/contracts/`.

## 3. Adapter binding (config-driven)
`apps/familyrobot` reads `FAMILYROBOT_PLATFORM` (or auto-detects) and builds the adapter set:

| Platform | audio | camera | home | power |
|---|---|---|---|---|
| desktop | portaudio | opencv_webcam | mock | none |
| android | termux | termux_or_ipcam | wifi_plug+esp | battery |
| raspberrypi | alsa_hat | picamera2 | gpio+wifi_plug | ups_hat |

No shared module imports an adapter; only `apps/familyrobot/wiring.py` does.

## 4. Core runtime (orchestrator)
- asyncio supervisor spawns workers: `audio`, `perception`, `cognition`, `expression`, `mqtt`, `web`.
- Internal **event bus** (asyncio queues) decouples workers; messages are typed dataclasses.
- Watchdog: each worker emits a heartbeat; supervisor restarts a stalled worker.
- Graceful degradation: local LLM OOM/timeout -> cloud LLM (if opted in) -> rule-based fallback.

## 5. Pipeline (end-to-end request flow)

```
AudioPort.read_frame -> wakeword("Hello Puppy") -> VAD segment -> STT(text, lang)
  -> [parallel] speaker_id(embedding) + face_id(embedding) -> identity_fusion(user)
  -> acl.check(user, intent) -> intent_router
       -> matched skill.execute(slots, user)  (skill -> HomePort/MQTT/etc.)
       -> else cognition.llm(prompt + rag_context(user))
  -> memory.write(user, episodic)            (if worth remembering)
  -> expression.tts(reply, lang) -> AudioPort.play -> ui_state(speaking)
...
```

## 6. Contract testing
- `tests/contracts/test_<port>.py` defines behaviour every adapter must satisfy.
- Parametrize over available adapters; CI matrix runs amd64 (desktop) + arm64 (pi/android).
- An adapter is "done" only when it passes its port's contract suite.
