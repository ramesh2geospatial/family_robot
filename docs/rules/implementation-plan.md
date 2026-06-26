# FamilyRobot – Build Plan for Agentic LLM (Antigravity / Gemini Flash)

> Self-contained, ordered implementation plan. An autonomous coding agent can follow these steps to build FamilyRobot from an empty repo. Each step lists the goal, files to create, and a verifiable acceptance check. Build **Desktop first**, then Android, then Pi.

## Conventions
- Read [architecture.md](./architecture.md), [tech-stack.md](./tech-stack.md), [skills-catalog.md](./skills-catalog.md), [testing-strategy.md](./testing-strategy.md), [progress-ledger.md](./progress-ledger.md) before coding.
- Shared code -> `packages/`; hardware code -> `adapters/`. Shared imports ports only.
- **Track progress in `BUILD_STATE.md`** (repo root) after every step so the build is resumable.
- After each step, run the step's **test gate** (see testing-strategy.md). Do not proceed if red.

## Stage D0 – Build harness (do this before Step 1)
- Create `BUILD_STATE.md` from the progress-ledger template; set up `tests/{unit,contracts,functional,business,regression}/`, `pyproject.toml` test markers, `ruff`/`black` config, and a `pytest` smoke test.
- **Check:** `pytest -q` runs (zero tests OK); `BUILD_STATE.md` exists and is committed.

## Stage D1 – Desktop (target: full assistant on laptop, mock smart-home)

### Step 1 – Project skeleton
- Create the monorepo layout (architecture.md §1), `pyproject.toml` with extras, `.gitignore` (models, secrets, data).
- **Check:** `pip install -e ".[desktop]"` succeeds; `python -m apps.familyrobot --help` runs.

### Step 2 – Ports + config + wiring
- Implement `packages/ports/*` (audio, camera, home, power, notify) as Protocols.
- `packages/core/config.py` (pydantic) loads `config/base.yaml` + `config/<platform>.yaml`.
- `apps/familyrobot/wiring.py` selects adapters by platform.
- **Check:** loading `desktop.yaml` returns a wired adapter set; unit test passes.

### Step 3 – Desktop adapters
- `adapters/desktop/audio.py` (PortAudio), `camera.py` (OpenCV webcam), `home.py` (mock, logs), `power.py` (no-op).
- Add `tests/contracts/test_audio_port.py`, `test_home_port.py`; desktop adapters must pass.
- **Check:** contract tests green; mic records 1s, speaker plays a tone.

### Step 4 – Perception
- `packages/perception/`: wakeword (openWakeWord "Hello Puppy"), VAD (silero), STT (faster-whisper small).
- **Check:** saying "Hello Puppy" then a sentence prints transcribed text with detected language.

### Step 5 – Cognition + memory
- `packages/cognition/`: `llm_client` (llama.cpp local + optional cloud), `memory` (SQLite WAL + sqlite-vec), `rag`, `intent_router`.
- **Check:** ask a question -> LLM answers; "remember X" persists; restart -> "what did I ask you to remember?" recalls X.

### Step 6 – Expression + loop
- `packages/expression/tts.py` (Piper en/hi/mr) + `ui_state`. Wire the full pipeline (architecture.md §5).
- **Check:** end-to-end "Hello Puppy, what's the weather joke" -> spoken reply.

### Step 7 – Governance
- `packages/governance/`: identity_fusion (face+voice), acl (role matrix), audit_log.
- **Check:** a "child" user is denied a geyser command with a polite spoken refusal (mock).

### Step 8 – First skills
- `packages/skills/`: `lights` (mock home), `reminders`, `memory_admin`, `assistant` fallback.
- **Check:** "turn on the living room light" logs `LIGHT ON` via mock HomePort; reminder fires.

### Step 9 – Companion PWA
- `packages/webapp/`: FastAPI + PWA. Enroll member (webcam+mic), manual control, memory review.
- **Check:** phone on same Wi-Fi opens `http://<laptop-ip>:8080`, enrolls 1 face+voice, toggles the mock light.

### Step 10 – Dockerize (dev)
- `deploy/docker/`: Dockerfile (`python:3.11-slim-bookworm`) + compose (`core`, `mqtt`, `web`). Multi-arch via buildx.
- **Check:** `docker compose up` runs the stack; audio adapter may run on host if container audio is blocked.

**Stage D1 done when:** every row of the Desktop column in spec §2X.8 passes.

## Stage D2 – Android (target: same app on a spare phone)

### Step 11 – Android adapters
- `adapters/android/`: audio (Termux mic), camera (Termux or IP-cam), home (Wi-Fi plug + ESP32 over MQTT), power (battery API).
- `deploy/android-termux/setup.sh`: install proot Debian + deps + autostart; foreground service; disable battery optimization.
- **Check:** Android adapters pass the same contract suites; wake->reply works on the phone.

### Step 12 – Real network smart-home
- `packages/home/`: MQTT client + Tasmota/ESPHome plug driver + Broadlink/ESP IR. Replace mock with a real Wi-Fi plug.
- **Check:** "turn on the fan" toggles a real Wi-Fi plug from the phone.

**Stage D2 done when:** Android column of §2X.8 passes; phone runs 24h unattended.

## Stage 1+ – Raspberry Pi 5 (target: full hardware)

### Step 13 – Pi adapters
- `adapters/raspberrypi/`: audio (ALSA/ReSpeaker HAT), camera (picamera2), home (`lgpio` GPIO relay + Wi-Fi plug), power (UPS HAT + safe shutdown).
- `deploy/raspberrypi/`: systemd units, install script, OS notes, nftables, MQTT TLS.
- **Check:** Pi adapters pass contract suites; GPIO relay toggles a real light; UPS triggers clean shutdown on power loss.

### Step 14 – Harden & ship
- Encrypt memory DB (SQLCipher/LUKS), signed OTA update path, IoT VLAN, hardware mic-mute + appliance override.
- **Check:** security checklist (spec §5/§10) all pass; full DoD matrix green on Pi.

## Global acceptance (project complete for Phase 1-2)
- All three platform columns of §2X.8 pass from one shared codebase.
- Privacy: no raw audio/video/memory leaves device unless a cloud feature is explicitly opted in.
- Safety: all mains-voltage appliances via certified plug/contactor + hardware override.
- Reliability: survives power cut (UPS + WAL), watchdog auto-restart.
