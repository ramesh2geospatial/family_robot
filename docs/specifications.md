# Family Companion Robot – Technical Specification (v3)

> **Status:** Planning / specification only. No code in this document.  
> **Scope:** A low-cost, modular, secure, feature-rich, voice-first **family companion + home-automation robot** for an 8-member Indian household, running on a Raspberry Pi.  
> **Companion docs:** [project_brief.md](../prompts/project_brief.md), [hardware/BOM.md](../hardware/BOM.md)

---

## 0. Design Principles

1. **Local-first & private** – voice, vision, and family memory are processed and stored on-device by default. Cloud is opt-in, per-feature, and never receives raw memory.
2. **Modular** – every capability is a self-contained, hot-swappable **skill plugin** behind a stable interface. Add/remove features without touching the core.
3. **Latest, but proven (2026)** – use current best-in-class open-source models (Kokoro/Piper TTS, faster-whisper/Moonshine STT, Qwen2.5/Llama 3.2/Gemma 2 LLMs, openWakeWord) that run on modest ARM CPUs.
4. **Low-cost & repairable** – commodity parts, BIS-marked electricals, 3D-printable enclosure, no vendor lock-in, no mandatory subscriptions.
5. **Fail-safe** – power-cut resilient (UPS), watchdog-restarted services, hardware override for every appliance; the robot is a convenience layer, never a single point of failure.
6. **Secure by default** – encrypted data at rest, network-segmented, signed updates, least-privilege per family role.
7. **Inclusive** – multilingual (English / Hindi / Marathi + code-mixing), accessible to kids and elders, no smartphone required for daily use.

---

## 1. System Overview

```
                        FAMILY ROBOT (Raspberry Pi)
         ┌─────────────────────────────────────────────────────────────┐
         │                                                             │
Mic ────>│ Wake Word ───> VAD ───> STT ───> Intent Router              │
Array    │                                     │                       │
         │                                     ▼                       │
         │ Face-ID ──┐                   ┌───────────┐                 │
Pi ─────>│           ├─> Identity ──────>│           │                 │
Camera   │ Speaker-ID│   Fusion          │Orchestrator                 │
         │           │                   │(async core)                 │
         │           └──────────────────>│Skill Reg  │                 │
         │                               │Memory(RAG)│                 │
         │                               │Policy/ACL │                 │
         │                               └─────┬─────┘                 │
         │                                     │                       │
         │                 ┌───────────────────┼───────────────────┐   │
         │                 ▼                   ▼                   ▼   │
         │             Local LLM           Cloud LLM          Smart-Home│
         │            (llama.cpp)          (opt-in)            & Media │
         │                 │                   │               Skills  │
         │                 └───────────┬───────┘                   │   │
         │                             ▼                           ▼   │
         │                            TTS ───> Speaker             │   │
         │                                                         │   │
         └─────────────────────────────┬───────────────────────────┼───┘
                                       │                           │
                                       ▼                           ▼
                                  Zero Satellites             GPIO Relays,
                                  (kitchen/bed)            Wi-Fi Smart Plugs,
                                                             IR Blasters,
                                                             Zigbee Hub
                                                       [Connected via MQTT (TLS)]
```

- **Brain:** Raspberry Pi 4 (4 GB) baseline; **Pi 5 (8 GB)** is the recommended upgrade for fully-local LLM + vision concurrency.
- **Bus:** local **MQTT (Mosquitto, TLS)** connects the core to relays, plugs, IR, sensors, and satellite units.
- **Network:** dedicated **IoT Wi-Fi SSID / VLAN**, isolated from the family's main network.

> **Note:** the diagram shows the Raspberry Pi production target. The **same software** also runs on Desktop (development) and Android (Termux) – only the hardware adapter layer changes (see §2X). On Desktop/Android the GPIO block is replaced by mock/Wi-Fi/ESP32 drivers.

---

## 2. Modular Architecture

### 2.1 Layered design

| Layer | Responsibility | Swap freedom |
|:---|:---|:---|
| **Hardware Abstraction (HAL)** | GPIO, audio, camera, relays, IR, MQTT | Replace a relay with a smart plug w/o code changes elsewhere |
| **Perception** | Wake word, **AEC/barge-in**, VAD, STT, Face-ID, Speaker-ID | Swap whisper.cpp <-> Vosk <-> Moonshine via config |
| **Cognition** | Intent router, Local/Cloud LLM, RAG memory | Swap Qwen <-> Llama <-> Gemma; local <-> cloud per query |
| **Action (Skills)** | Plugins: lights, fan, AC, pump, music, cooking, dance, homework, reminders, calls | Each skill is an independent package with a manifest |
| **Expression** | TTS, RGB ring, OLED face, app notifications | Swap Piper <-> Kokoro voices |
| **Governance** | Identity fusion, ACL/permissions, policy, audit log | Central, security-critical |

> **Full-duplex voice:** the audio front-end runs **acoustic echo cancellation (AEC)** + noise suppression (WebRTC APM / `speexdsp`) so the robot can hear a wake word **while it is speaking** and support **barge-in** (interrupting TTS). Without this, far-field voice feels broken; it is required for a sellable device.

### 2.2 Skill plugin contract (concept)

Each skill ships a manifest declaring: `name`, `languages`, `intents/utterances`, `required_permissions`, `hardware_deps`, `offline_capable`, `entry_points`. The orchestrator discovers skills at boot, registers their intents, and routes matched utterances. Unknown/ambiguous utterances fall through to the LLM. This keeps the system **extensible without core edits**.

### 2.3 Process & reliability model

- **One supervisor** (systemd + internal asyncio) spawns isolated workers: `audio`, `stt`, `llm`, `vision`, `mqtt`, `web`.
- **Watchdog**: each worker heartbeats; a hung worker is restarted without killing audio.
- **Graceful degradation**: if local LLM OOMs, auto-route to cloud (if opted in) or to a rule-based fallback.
- **State**: durable in SQLite; transient in memory; safe to power-cut at any moment (WAL + UPS).

---

## 2X. Cross-Platform Modular Design (Desktop -> Android -> Raspberry Pi)

**Development order:** (1) **Desktop/laptop** -> (2) **Android phone** -> (3) **Raspberry Pi**.  
**Core rule:** write each capability **once**. Code is split into **shared, platform-agnostic modules** and thin **platform-specific adapters**. Only the parts that physically differ per device are written separately; everything else is shared and reused unchanged.

### 2X.1 The "ports & adapters" (hexagonal) approach

The application core depends only on **interfaces (ports)**, never on a concrete device. Each platform supplies an **adapter** that implements the port. Swapping desktop <-> Android <-> Pi means swapping adapters via config – **no change to shared code**.

```
SHARED (write once, runs everywhere)
┌────────────────────────────────────────────────────────┐
│ orchestrator · intent router · skills · memory/RAG ·   │
│ LLM client · TTS/STT engines · policy/ACL ·            │
│ MQTT client · PWA/web app · config · logging · models  │
└───────────────────────┬────────────────────────────────┘
                        │ depends on PORTS only
                        ▼
┌──────────────┬──────────────┬──────────────┬───────────┐
│  HomePort    │  AudioPort   │  CameraPort  │ GpioPort  │
└──────┬───────┴──────┬───────┴──────┬───────┴─────┬─────┘
       │              │              │             │
┌──────▼──────┐┌──────▼──────┐┌──────▼──────┐┌─────▼─────┐
│Desktop Adap ││Desktop Adap ││Desktop Adap ││Mock Gpio  │
│(mock)       ││(PortAudio)  ││(Webcam/CV2) ││(Log only) │
└─────────────┘└─────────────┘└─────────────┘└───────────┘
┌─────────────┐┌─────────────┐┌─────────────┐┌───────────┐
│Android Adap ││Android Adap ││Android Adap ││No Gpio    │
│(Wi-Fi/ESP)  ││(Termux Mic) ││(Termux Cam) ││(Wi-Fi only)│
└─────────────┘└─────────────┘└─────────────┘└───────────┘
┌─────────────┐┌─────────────┐┌─────────────┐┌───────────┐
│Pi Adapter   ││Pi Adapter   ││Pi Adapter   ││Pi Gpio    │
│(GPIO/plugs) ││(ALSA/HAT)   ││(Picamera2)  ││(lgpio)    │
└─────────────┘└─────────────┘└─────────────┘└───────────┘
```

### 2X.2 What is SHARED vs PLATFORM-SPECIFIC

| Module | Shared? | Notes |
|:---|:---:|:---|
| Orchestrator / supervisor | ☑ Shared | pure Python asyncio |
| Intent router | ☑ Shared | - |
| Skills (lights, music, cooking, dance, homework, reminders, calls) | ☑ Shared | talk to ports, never to hardware directly |
| Memory / RAG (SQLite + vector) | ☑ Shared | SQLite runs on all three |
| LLM client (local + cloud) | ☑ Shared | backend chosen by config (llama.cpp/Ollama/cloud) |
| STT / TTS / wake-word engines | ☑ Shared | CPU models run on all three; **audio I/O** is via AudioPort |
| Face-ID / Speaker-ID logic | ☑ Shared | frame/sample source is via Camera/Audio ports |
| Policy / ACL / audit | ☑ Shared | security-critical, identical everywhere |
| MQTT client | ☑ Shared | same broker protocol |
| Companion PWA / web app | ☑ Shared | served by the host, opened on phone |
| Config / logging / utils | ☑ Shared | - |
| **Audio adapter** | ┱ Per-platform | Desktop: PortAudio/PyAudio · Android: Termux/`termux-microphone` or Pulse · Pi: ALSA/ReSpeaker HAT |
| **Camera adapter** | ┱ Per-platform | Desktop: OpenCV/webcam · Android: Termux camera/IP-cam · Pi: `picamera2` CSI |
| **GPIO/relay adapter** | ┱ Per-platform | Desktop: **mock** (logs) · Android: **none** (Wi-Fi/ESP only) · Pi: `lgpio`/`gpiozero` |
| **Power/UPS adapter** | ┱ Per-platform | Desktop: n/a · Android: battery API · Pi: UPS HAT |
| **Notifications** | ┱ Per-platform (thin) | Desktop: log/web · Android: native/WebPush · Pi: WebPush/ntfy |

> **Compatible modules are shared; only incompatible modules are written separately** – exactly the requested model.

### 2X.3 Package / repository layout (monorepo, shared libraries)

```
familyrobot/
├── packages/
│   ├── core/                  # SHARED library: orchestrator, intent router, config, logging, utils
│   │   ├── ports/             # SHARED: abstract interfaces (AudioPort, CameraPort, HomePort, NotifyPort, PowerPort)
│   │   ├── perception/        # SHARED: wakeword, vad, stt, speaker_id, face_id (device-agnostic logic)
│   │   ├── cognition/         # SHARED: llm_client, memory (SQLite+vector/RAG), rag
│   │   ├── expression/        # SHARED: tts, ui_state (ring/face abstractions)
│   │   ├── skills/            # SHARED: lights, fan, ac, pump, music, cooking, dance, homework, reminders, calls
│   │   ├── home/              # SHARED: mqtt client, smart-plug & IR drivers (network-based, work everywhere)
│   │   ├── governance/        # SHARED: identity fusion, acl, policy, audit
│   │   └── webapp/            # SHARED: companion PWA (FastAPI + frontend)
│   │
│   ├── adapters/              # PLATFORM-SPECIFIC implementations of ports
│   │   ├── desktop/           # audio (PortAudio), camera (webcam), home (mock relay), power (n/a)
│   │   ├── android/           # audio (Termux), camera (Termux/IP-cam), home (Wi-Fi/ESP only), power (battery)
│   │   └── raspberrypi/       # audio (ALSA/HAT), camera (picamera2), home (lgpio GPIO + plugs), power (UPS HAT)
│   │
│   └── apps/
│       └── familyrobot/       # thin entrypoint: loads config, picks adapter set, starts core
│
├── deploy/
│   ├── docker/                # Dockerfile + docker-compose (desktop dev, multi-arch build for Pi)
│   ├── android-termux/        # setup script: proot Debian + deps + autostart
│   └── raspberrypi/           # systemd units, install script, OS image notes
│
├── models/                    # downloaded once, shared via volume (wake/STT/LLM/TTS/embeddings)
├── config/                    # base.yaml + desktop.yaml + android.yaml + raspberrypi.yaml (overrides)
└── tests/                     # shared unit tests run on every platform in CI
```

### 2X.4 How a platform is selected

- `config/base.yaml` holds all shared settings. Each platform file (`desktop.yaml` / `android.yaml` / `raspberrypi.yaml`) **only overrides the adapter bindings**, e.g.:
  - Desktop: `audio: portaudio`, `camera: webcam`, `home: mock`
  - Android: `audio: termux`, `camera: termux`, `home: wifi_plug+esp`
  - Pi: `audio: alsa_hat`, `camera: picamera2`, `home: gpio+wifi_plug`
- The entrypoint reads `FAMILYROBOT_PLATFORM` (or auto-detects) and wires the matching adapters into the shared core. **Shared code never imports a platform module directly** – only ports.

### 2X.5 Build & reuse mechanics

- **One Python package set** installed everywhere; platform extras via `pip install familyrobot[desktop|android|pi]` so heavy/native deps (e.g., `lgpio`, `picamera2`) install **only where they work**.
- **Adapters are optional dependencies** – Android won't pull `lgpio`; Pi won't pull desktop webcam libs.
- **CI matrix** runs shared unit tests on amd64 (desktop) + arm64 (Pi/Android) and builds the multi-arch Docker image, so a change to shared code is validated for all targets at once.
- **Same code path** for desktop Docker, Android Termux, and Pi – only the adapter layer + config differ.

### 2X.6 Three-stage development plan mapped to modules

| Stage | Target | New work | Reused unchanged |
|:---|:---|:---|:---|
| **1. Desktop** | Laptop (Docker/WSL2) | `adapters/desktop` (audio, webcam, **mock** home) | - (everything else built here, shared) |
| **2. Android** | Spare phone (Termux) | `adapters/android` (audio, camera, Wi-Fi/ESP home) + `deploy/android-termux` | **all** of `packages/*` (core, skills, memory, LLM, STT/TTS, webapp) |
| **3. Raspberry Pi** | Pi 5 | `adapters/raspberrypi` (ALSA/HAT, picamera2, GPIO, UPS) + `deploy/raspberrypi` | **all** of `packages/*` + skills + webapp |

> Net effect: ~80% of the codebase is written **once in Stage 1** and reused verbatim on Android and the Pi. Each later stage only adds a small platform adapter folder.

### 2X.7 Port contract testing (guarantees reuse works)

- Every **port** ships a **shared contract test suite** (e.g., `test_audio_port`, `test_camera_port`, `test_home_port`).
- **Every adapter** (desktop/android/pi/mock) must pass the *same* suite, so a new platform is "done" only when it satisfies the identical behavioural contract. This prevents platform drift and proves the shared modules truly work everywhere.
- CI runs contract tests per adapter on its native arch; shared `packages/*` tests run once on all arches.

### 2X.8 Per-platform Definition of Done (acceptance criteria)

| Capability | Desktop (D1) | Android (D2) | Raspberry Pi (Stage 1) |
|:---|:---:|:---:|:---:|
| Wake "Hello Puppy" | ☑ | ☑ | ☑ |
| AEC + barge-in (interrupt TTS) | ┱ | ☑ | ☑ |
| STT -> LLM -> TTS (en/hi/mr) | ☑ | ☑ | ☑ |
| Family enroll (face+voice) | ☑ (webcam) | ☑ (phone cam) | ☑ (Pi cam) |
| Long-term memory persists across restart | ☑ | ☑ | ☑ |
| Smart-home command | ☑ mock (log) | ☑ Wi-Fi/ESP plug | ☑ GPIO relay + plug |
| Companion PWA reachable from phone | ☑ | ☑ | ☑ |
| All shared `packages/*` contract tests pass | ☑ | ☑ | ☑ |
| Runs unattended 24h without crash | optional | ☑ | ☑ |

A platform is **"compatible & done"** only when every row in its column passes.

---

## 3. Software Stack (2026, pinned choices)

> **Default = commercial-safe & open.** Every primary component is OSS **and** permits commercial use, so the same build is usable for a personal robot **and** a sellable product. Watch model licenses (License column): some weights (e.g. Qwen2.5-3B) are research-only - the default LLM is therefore a clearly commercial-OK model.

| Function | Primary (local) | License (primary) | Alternative | Cloud fallback (opt-in) |
|:---|:---|:---|:---|:---|
| OS | Raspberry Pi OS Lite (Bookworm, 64-bit) | OSS (GPL/misc) | Ubuntu Server 24.04 | - |
| Wake word | **openWakeWord** (custom "Hello Puppy") | Apache-2.0 | microWakeWord, Porcupine | - |
| AEC / barge-in | **WebRTC APM** (`webrtc-audio-processing`) / `speexdsp` | BSD / Xiph | hardware AEC (ReSpeaker) | - |
| VAD | Silero VAD | MIT | webrtcvad | - |
| STT | **faster-whisper** `small` int8 | MIT (model: MIT) | Vosk (hi/en), Moonshine, distil-whisper | Azure / Google STT |
| Speaker-ID | **SpeechBrain** ECAPA-TDNN | Apache-2.0 | Resemblyzer | - |
| Face-ID | **InsightFace** (`buffalo_l`) | code MIT (model non-commercial) ⚠ | `face_recognition`/dlib (BSD) | - |
| LLM (chat) | **Llama 3.2 3B-Instruct Q4_K_M** via llama.cpp/Ollama | Llama Community (commercial OK <700M MAU) | Gemma 3 4B, Qwen3-4B (Apache), Phi-4-mini, Qwen2.5-3B (research-only ⚠) | OpenAI / Gemini / Groq |
| Memory/RAG | **SQLite** + `sqlite-vec` + `bge-small` embeddings | public-domain / MIT | Chroma, FAISS | - |
| TTS | **Piper** (en/hi/mr) | MIT | **Kokoro-82M** (Apache, higher quality, CPU) | Azure Neural / ElevenLabs |
| Pose (dance) | **MediaPipe Pose** / MoveNet | Apache-2.0 | - | - |
| Smart-home bus | **Mosquitto** (MQTT, TLS) | EPL/EDL | - | - |
| Home integration | optional **Home Assistant** (Wyoming satellite) | Apache-2.0 | standalone | - |
| App | **PWA** (FastAPI + HTMX/Svelte) on Pi | MIT | - | self-hosted ntfy for push |
| Container/services | systemd units (lean); Docker optional | OSS | - | - |

> Rationale: all primary components run **offline on ARM CPU**, fit the 4 GB budget when staged, and are actively maintained in 2026. Ollama is offered for easy model management on Pi 5; raw llama.cpp for tightest RAM control on Pi 4.
>
> **2026 model refresh (verify before pinning):** local LLM – **Llama 3.2/3.3 3B**, **Gemma 3 4B**, **Qwen3-4B (Apache-2.0)**, **Phi-4-mini**, **SmoLM3**; high-accuracy STT tier – **whisper-large-v3-turbo** / **distil-whisper** (desktop/cloud). Pick the newest *maintained, commercially-licensed* weight that fits the RAM budget.
>
> **⚠ Commercial-license watch-outs:**  
> (1) **Qwen2.5-3B** weights are research-only - do **not** ship them in a sold product; use Llama 3.2 / Gemma 3 / Qwen3-4B-Apache instead.  
> (2) **InsightFace** `buffalo_*` models are non-commercial - for a sold device, retrain/replace with a commercially-licensed face embedder or use `dlib` / `face_recognition` (BSD).

---

## 4. Feature Set (modular skills)

### 4.1 Conversation & assistant (Alexa-class, no subscription)

- Natural multi-turn chat (en/hi/mr + code-mix), persona "Puppy".
- General Q&A, definitions, math, conversions, jokes, stories.
- Memory-aware: recalls family facts via RAG.

### 4.2 Smart home

- Lights (on/off/dim), fans (speed), AC, geyser, water pump, washing-machine plug, TV (IR), mixer.
- Scenes & routines ("Good morning" = lights + news + weather + pump check).
- Schedules, conditional automations (sunset lights, geyser at 6 AM weekdays).
- Energy awareness (smart-plug metering where available).

### 4.3 Family & personalization

- Face + voice enrollment for 8 members; per-user greetings, preferences, language.
- **Role-based ACL**: parents (full), kids (no geyser/pump/purchases/late-night), guest (no memory writes).
- Quiet hours, study mode, sleep mode per user.

### 4.4 Long-term memory

- Per-person profiles, episodic notes, routines, shopping list, important dates.
- Encrypted SQLite + vector recall; decay + "forget me" right.
- Weekly spoken memory review.

### 4.5 Entertainment & learning

- **Music**: local library + streaming (reuse family's existing Spotify/YT Music/JioSaavn account).
- **Dance coach**: play song + MediaPipe pose scoring + feedback.
- **Cooking helper**: step-by-step recipes in hi/mr, parallel timers, unit conversion, substitutes.
- **Homework helper**: grade-level explanations, step-by-step math, quiz mode.
- **Kids' stories / rhymes**: sound machine, alarms, reminders.

### 4.6 Communication (Phase 2)

- **WhatsApp + voice calls to enrolled family only** (whitelist), voice-triggered with confirmation.
- Routed via the household **Android phone** (free, uses your number) or Twilio (paid, reliable).

### 4.7 Safety & awareness (Phase 2+)

- Unknown-face alert at night -> push to Android app.
- Smoke/gas/water-leak sensor hooks (Zigbee) -> spoken + push alert.
- Door/window sensors, presence-based automations.

---

## 5. Security & Privacy Specification

### 5.1 Data protection

- **Encryption at rest**: family DB via **SQLCipher**, or full-disk **LUKS** on the SSD. Keys stored in the Pi's secure key file with restrictive perms (and TPM/secure-element if added).
- **No raw audio/video persisted** unless debug mode is explicitly enabled (auto-expires).
- **Embeddings, not photos**: store face/voice embeddings; original media deleted post-enrollment unless user opts to keep.

### 5.2 Network

- Dedicated **IoT VLAN / guest SSID**; robot and smart plugs isolated from PCs/phones.
- **MQTT over TLS** with per-device credentials; no anonymous access.
- **No inbound ports** from the internet; remote access only via Tailscale/WireGuard if needed.
- Firewall (nftables) default-deny inbound.

### 5.3 Identity & access

- Multi-factor identity = **face + voice fusion** for sensitive actions (e.g., calls, purchases, geyser).
- **Role-based ACL** enforced centrally; every privileged action is logged to a tamper-evident **audit log**.
- Child-safety filter on LLM output; allow-list for web/content skills.

### 5.4 Software supply chain & updates

- **Signed OTA updates** (verify checksum/signature before apply); staged rollback.
- Pinned dependencies (lockfile), reproducible build, automatic OS security patches.
- **SBOM** generated per release (`syft`/`CycloneDX`); dependency + secret scanning (`pip-audit`, `gitleaks`) in CI; fail build on critical CVEs.
- Secrets in `secrets.env` (chmod 600), never in git; `.gitignore` enforced.

### 5.5 Physical

- **Hardware mic-mute** switch (cuts mic power, with LED indicator).
- **Hardware override** switch in parallel with every relay/contactor so appliances work if the Pi is down.
- Tamper-resistant enclosure for mains wiring; all 6 A+ loads via BIS-marked plugs/contactors in an enclosed box by a licensed electrician.

### 5.6 OWASP / IoT hardening checklist

- No default passwords; unique strong creds per service/device.
- Least privilege for the service user (no root for app).
- Input validation on all intents and web/app endpoints; rate-limit the app.
- Disable unused interfaces (Bluetooth/SSH password login -> key-only).
- Regular encrypted backups, tested restore.

### 5.7 Compliance & Productization (required only if sold as a product)

> Personal/DIY use can skip this. To **sell** the device (esp. in India) the following are mandatory – they are non-code gates, tracked separately from the build steps.

- **Data protection (DPDP Act 2023, India / GDPR-equiv):** face & voice embeddings are **sensitive/biometric personal data**, and the household includes **minors** – implement explicit **consent at enrollment**, a plain-language privacy notice, purpose limitation, the existing **"forget me" / erasure** right, and verifiable **parental consent** for children. Keep a Records-of-Processing note. Default local-first storage already minimizes exposure.
- **Electrical safety:** any mains-switching part shipped with the product needs **BIS/ISI**-marked components and a certified, enclosed mains module; provide a manual override. Liability for mains wiring stays with a licensed electrician unless the product is formally certified.
- **Radio & EMC (India):** Wi-Fi/BT/Zigbee radios require **WPC/ETA** equipment approval; the finished device needs **EMC/EMI** testing. (CE/FCC equivalents for export.)
- **Child-safety:** on-device LLM output filter + content allow-list (already in 5.3); document age-appropriateness and disable purchases/calls for kid roles.
- **Fleet OTA & provisioning:** signed-update server, per-device identity/onboarding, opt-in (not default) telemetry, and a documented update/rollback SLA.
- **Observability & support:** health endpoint + metrics (mic/speaker/camera/MQTT/model status), structured logs, crash reporting (opt-in), and a tested backup/restore + RMA path.
- **Manufacturable BOM:** the maker BOM (§9 / hardware/BOM.md) is for prototypes; a sold product needs a **volume BOM** (PCB/HAT, injection or tooled enclosure, per-unit-at-scale costing, warranty/returns). For scale-out compute, the documented **Orange Pi 5 / RK3588 (6 TOPS NPU)** is the cost/performance path vs. Pi 5.

---

## 6. Reliability & Power

- **UPS HAT** rides through Indian power cuts; on low battery -> safe shutdown (DB flushed, WAL checkpointed).
- **SQLite WAL** + periodic checkpoint; **hourly snapshot** to SSD; opt-in encrypted cloud backup.
- **systemd watchdog** + auto-restart; boot-time self-test (mic, speaker, camera, MQTT, models).
- Thermal: active-cooled case; CPU governor tuned; LLM throttles if temp > threshold.

---

## 7. Performance Budget

### 7.1 RAM (Pi 4, 4 GB) – staged loading

| Component | RAM | Load policy |
|:---|:---|:---|
| OS + Mosquitto + app | ~500 MB | always |
| Wake word + VAD | ~40 MB | always |
| STT (faster-whisper small int8) | ~400 MB | on speech |
| Speaker-ID + Face-ID | ~250 MB | lazy, on demand |
| Local LLM (3B Q4) | ~2.2 GB | on demand, unload on idle |
| Memory + embeddings | ~150 MB | always |
| TTS (Piper) | ~150 MB | on reply |
| Headroom | ~300 MB | buffers |

> On Pi 4, run **either** the local 3B LLM **or** vision-heavy tasks at a time; the orchestrator serializes heavy workloads. For always-on local LLM + concurrent vision, choose **Pi 5 (8 GB)**.

### 7.2 Latency targets

- Wake -> listening: < 300 ms.
- End-of-speech -> first TTS audio: < 1.5 s (cloud LLM) / < 3 s (local 3B on Pi 4) / < 1.2 s (Pi 5).
- Smart-home command execution: < 500 ms (MQTT/relay).

---

## 7A. Develop-First Strategy: Laptop (Docker) -> Raspberry Pi

**Goal:** build and validate as much as possible on the laptop **before spending money on hardware**. Only buy the Pi once the core voice + assistant loop works on the laptop.

### 7A.1 Why this works

- The entire stack is **plain Linux + Python**; the only Pi-specific parts are **GPIO, camera CSI, and HAT audio**. Everything else (wake word, STT, LLM, TTS, memory, MQTT, skills, the PWA) runs identically on a laptop.
- A **Linux Docker container** on the laptop gives the same OS environment we'll deploy to the Pi (Debian Bookworm, ARM -> build multi-arch images). This avoids "works on my machine" surprises.
- The family can **test basic functionality immediately** using the **laptop mic/speaker/webcam** and a **phone browser** (the companion PWA), with **zero hardware purchase**.

### 7A.2 What is emulated vs real on the laptop

| Capability | On laptop (dev) | On Raspberry Pi (prod) |
|:---|:---|:---|
| Wake word / STT / LLM / TTS | **Real** (laptop CPU/GPU - faster) | Real (ARM CPU) |
| Mic / Speaker | Laptop built-in or USB | ReSpeaker HAT / USB |
| Camera / Face-ID | Laptop webcam | Pi Camera 3 |
| Memory (SQLite + vector) | **Real** | Real |
| MQTT broker | **Real** (Mosquitto in Docker) | Real |
| Companion PWA (phone) | **Real** (served from laptop over Wi-Fi) | Real (served from Pi) |
| GPIO relays (lights/fan) | **Mock driver** (logs "LIGHT ON") | Real (`gpiozero`/`lgpio`) |
| Smart plugs / IR | **Mock or real** (Wi-Fi plugs work from laptop too) | Real |

> **Hardware Abstraction Layer (HAL)** makes this swap a one-line config change: `home.driver: mock` on the laptop -> `home.driver: gpio` on the Pi. No application code changes.

### 7A.3 Container & portability plan

- **Base image:** `python:3.11-slim-bookworm` (matches Pi OS Bookworm).
- **Build multi-arch** with `docker buildx` (`linux/amd64` for laptop, `linux/arm64` for Pi) so the *same image* deploys to both.
- **docker-compose** services: `core` (orchestrator+skills), `mqtt` (Mosquitto), `web` (PWA), optional `ollama` (LLM). Volumes for `models/` and `data/` so models download once.
- **Audio into Docker:** pass host audio via PulseAudio/ALSA socket (Linux) or run the audio worker natively on the host and the rest in Docker (simplest cross-platform path, incl. Windows laptop via WSL2).
- **Phone testing:** PWA exposed on the laptop's LAN IP; phone on same Wi-Fi opens `http://<laptop-ip>:8080` to enroll faces/voices and send commands.

### 7A.4 Windows laptop note

This dev box is Windows. Run the Linux container under **WSL2 + Docker Desktop** (or Rancher Desktop). Do AI/voice work inside the WSL2 Linux environment so it mirrors the Pi exactly. The phone still connects over Wi-Fi to the laptop's IP.

### 7A.5 Exit criteria before buying the Pi

Buy hardware only after the laptop build demonstrates:
1. "Hello Puppy" wake word triggers reliably.
2. Speech -> text -> LLM -> spoken reply in English/Hindi/Marathi.
3. At least one **mock** smart-home command ("turn on the light") routes through MQTT and logs success.
4. Family enrollment (face + voice) of 1-2 people works from the phone PWA.
5. Long-term memory stores and recalls a fact across restarts.

---

## 7B. Alternative Deployment Target: Android Phone

A spare **Android phone can host FamilyRobot**, either as the main brain (all-wireless setup) or as a satellite node. It is a strong option because the phone already bundles hardware a Pi must buy separately.

### 7B.1 Docker on Android – reality

- **Stock Android cannot run Docker** (no Docker daemon; Docker needs a Linux kernel with cgroups + root).
- **You don't need Docker on the phone.** Run the *same Python codebase* inside **Termux + `proot-distro`** (Debian Bookworm) – a Linux userland that mirrors the Pi/Docker environment. Same code, same dependencies, no image required.
- Optional: rooted phones or those with kernel cgroup support can run real containers, but this is **not recommended** (fragile, voids warranty).

### 7B.2 What the phone gives you for free

| Built-in on phone | Equivalent Pi accessory saved |
|:---|:---|
| Mic + speaker | ReSpeaker HAT + speaker (~₹4,000) |
| Camera (face-ID) | Pi Camera 3 (~₹2,800) |
| Touchscreen UI / puppy face | OLED/LCD (~₹450-1,800) |
| Battery | UPS HAT (~₹2,500) |
| Wi-Fi/BT + often faster SoC than Pi | - |

A spare phone can replace ~₹12,000 of Pi accessories.

### 7B.3 The key limitation – no GPIO

- A phone has **no GPIO pins**, so it **cannot drive relays directly**.
- Smart-home control must go fully **wireless**: Wi-Fi smart plugs, **MQTT**, **ESP32/ESP8266** relay nodes, IR blasters, Bluetooth, or Zigbee USB (via OTG).
- This matches the path already chosen for geyser/AC/pump/washer; only the cheap GPIO relay board for lights/fan would be replaced by a Wi-Fi/ESP relay node.

### 7B.4 Other Android caveats

- **Background limits / Doze:** keep the app foreground (persistent notification) or use a kiosk launcher; disable battery optimization for it.
- **Thermal & longevity:** a phone running 24x7 needs ventilation and a charge-limit setup to avoid battery swelling.
- **OS updates / fragmentation:** Termux behavior varies by Android version; pin a known-good device.
- **Audio latency:** generally fine; far-field "across the room" pickup is weaker than a dedicated mic array.

### 7B.5 Recommended deployment patterns

| Pattern | Brain | Smart-home I/O | Best when |
|:---|:---|:---|:---|
| **A. Pi-centric** (default) | Raspberry Pi 5 | GPIO relays + Wi-Fi plugs | Hard-wired control, best far-field mic |
| **B. Android-brain (all-wireless)** | Spare Android phone (Termux) | Wi-Fi plugs + ESP32 nodes (no GPIO) | Reuse a spare phone, minimal spend, no hard-wiring |
| **C. Hybrid** | Pi 5 = brain; phones = satellites/PWA | Pi GPIO + plugs; phones for voice/vision in other rooms | Whole-home coverage |

> **Verdict:** Develop once (laptop Docker), deploy anywhere. Android is an excellent **D2 satellite** and a viable **all-wireless brain**; the **Pi 5 stays recommended** when you want hard-wired GPIO relays and a dedicated far-field mic. Phase D code should keep the HAL clean so the "same code" runs on laptop, Pi, and Android-Termux unchanged.

---

## 8. Phased Roadmap

| Phase | Deliverables | Where it runs | Cost | Effort |
|:---|:---|:---|:---|:---|
| **D1 – Desktop (Docker/WSL2)** | Build all shared `packages/*` + `adapters/desktop` (audio, webcam, **mock** home). Full voice loop + memory + PWA, tested via laptop & phone browser | **Laptop** | **₹0** | 3-5 weekends |
| **D2 – Android (Termux)** | Add `adapters/android` (mic/cam, Wi-Fi/ESP home) + autostart. **Reuse all shared packages unchanged.** Phone becomes a working robot/satellite | **Spare Android phone** | **₹0** | 1-2 weekends |
| **Stage 0 – Pi foundation** | Flash Pi OS, deploy same image, `adapters/raspberrypi`, OS/MQTT/security baseline | Raspberry Pi 5 | buy Pi kit | 1 weekend |
| **Stage 1 – Core voice on Pi** | Real mic/speaker/camera; lights/fan via real GPIO relay; enrollment; memory | Raspberry Pi 5 | + relay/mic/cam | 2-3 weekends |
| **Stage 2 – Smart home + Alexa-class** | Smart plugs (geyser/AC/pump/washer), IR (TV), music (YouTube+local), cooking, homework, dance | Raspberry Pi 5 | + plugs, IR | 4-6 weekends |
| **Stage 3 – Comms + presence** | WhatsApp/calls via Android phone, satellites, sensors, security mode, OLED/puppy face | Raspberry Pi 5 (+satellites) | + Pi Zero, Zigbee | ongoing |

> **Key change:** development now follows **Desktop -> Android -> Pi**. Stages D1-D2 cost **₹0**; only `adapters/*` differ between targets while all `packages/*` are shared and reused unchanged (see §2X).

---

## 9. Cost Summary (see [BOM](../hardware/BOM.md) for line items & links)

| Tier | One-time hardware | Recurring |
|:---|:---|:---|
| **Lean MVP** (Phase 0-1, Pi 4, relay only, basic mic) | **~₹18,000-22,000** | ₹0 |
| **Recommended** (Phase 1-2, Pi 4 + plugs + camera + IR + UPS + PWA) | **~₹30,000-34,000** | ₹0 mandatory |
| **Premium/Future-proof** (Pi 5 8 GB, full sensors, satellites) | **~₹45,000-55,000** | ₹0 mandatory |
| Optional cloud LLM/STT (opt-in, cached) | - | **~₹500/month** |

> No Alexa/Google subscription. Music reuses the family's existing streaming account. Everything works fully offline at ₹0 recurring.

---

## 10. Open Decisions (to finalize before purchase)

1. ~~Brain~~ - **Locked: Raspberry Pi 5 (8 GB).**
2. ~~Budget tier~~ - **Locked: Recommended.**
3. ~~Music~~ - **Locked: YouTube / YouTube Music + local MP3.**
4. ~~WhatsApp/calls~~ - **Locked: via family Android phone.**
5. ~~Enclosure~~ - **Locked: both tabletop + puppy shells.**

**All hardware decisions are locked.** Next action is **Phase D** (build & test on the laptop in Docker at ₹0); buy the Pi only after Phase D exit criteria (§7A.5) pass.
