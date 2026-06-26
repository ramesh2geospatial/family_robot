# FamilyRobot - Tech Stack & Model Reference (pinned, 2026)

> Concrete dependencies, model files, and install notes for implementation. Use these unless a newer maintained release is verified to work on ARM CPU within the RAM budget.

## 1. Runtime
- **Python:** 3.11 (matches Raspberry Pi OS Bookworm).
- **Async:** stdlib `asyncio`. Web: **FastAPI** + `uvicorn`. Frontend: PWA (HTMX or Svelte) served by FastAPI.
- **Config:** `pydantic` + `pyyaml`. Logging: stdlib `logging` with rotating file handler.

## 2. AI components (local-first)
| Function | Package / model | Notes |
|---|---|---|
| Wake word | `openwakeword` | train custom "Hello Puppy"; ~30 MB |
| AEC / barge-in | `webrtc-audio-processing` (APM) or `speexdsp` | echo-cancel so wake word works while speaking; enables interrupt-TTS |
| VAD | `silero-vad` (torch) or `webrtcvad` | segment speech |
| STT | `faster-whisper` model `small` int8 | multilingual en/hi/mr; ~400 MB RAM |
| STT (alt, lighter) | `vosk` en + hi small models | ~250 MB, lower accuracy |
| Speaker-ID | `speechbrain` ECAPA-TDNN | 192-d embeddings; cosine match |
| Face-ID | `insightface` (buffalo_s) + `onnxruntime` | embeddings only; delete raw photos. ⚠ model weights **non-commercial** - for a sold product use `dlib` / `face_recognition` (BSD) or a commercially-licensed embedder |
| LLM (local) | `llama-cpp-python` + **Llama 3.2 3B-Instruct Q4_K_M** (.gguf) | ~2.2 GB; commercial-OK (Llama Community). Alts: Gemma 3 4B, **Qwen3-4B** (Apache-2.0), Phi-4-mini. ⚠ **Qwen2.5-3B** = research-only, don't ship it |
| LLM mgmt (alt) | **Ollama** | easy model pull on Pi 5 / desktop |
| Embeddings | `bge-small-en` (or multilingual `bge-m3` small) via `sentence-transformers` or llama.cpp | for RAG |
| Vector store | **sqlite-vec** extension on SQLite | single-file, no server |
| TTS | **piper-tts** voices: en_US, hi_IN, mr_IN | fast CPU; ~150 MB |
| TTS (alt, nicer) | **Kokoro-82M** | higher quality, still CPU |
| Pose (dance) | `mediapipe` Pose or MoveNet (tflite) | Phase 2 |

## 3. Cloud fallback (opt-in only)
- LLM: OpenAI / Gemini / Groq via official SDKs. STT: Azure/Google. TTS: Azure Neural/ElevenLabs.
- Gated behind `cloud.enabled` per feature in config; **never** send raw memory rows.

## 4. Smart home / IoT
- **MQTT broker:** Mosquitto (TLS, per-device creds).
- Python MQTT: `paho-mqtt` or `aiomqtt`.
- Wi-Fi plugs: prefer **Tasmota/ESPHome** (local MQTT/HTTP) over Tuya cloud. TP-Link Tapo via `python-kasa`.
- IR: Broadlink via `python-broadlink`, or ESP-Tasmota IR over MQTT.
- Pi GPIO: `lgpio` (Pi 5) / `gpiozero`. ESP32 nodes: ESPHome firmware speaking MQTT.

## 5. Storage & security
- **SQLite** (WAL mode) for structured memory; **SQLCipher** (`pysqlcipher3`) or LUKS for encryption at rest.
- Secrets in `secrets.env` (chmod 600), loaded via env; never commit. `.gitignore` must cover `models/`, `*.gguf`, `secrets.env`, `data/`, `config.local.yaml`.
- TLS certs for MQTT; nftables default-deny inbound; SSH key-only.

## 6. Platform extras (pyproject optional-dependencies)
```toml
[project.optional-dependencies]
desktop = ["pyaudio", "opencv-python", "sounddevice"]
android = ["sounddevice"]                      # GPIO/picamera excluded on purpose
pi = ["lgpio", "picamera2", "gpiozero"]
cloud = ["openai", "google-generativeai"]
```
Install per target: `pip install -e ".[desktop]"` / `".[pi]"` / `".[android]"`.

## 7. RAM budget (Pi 4 / 4 GB – stage loads)
OS+MQTT ~500 MB · wake+VAD ~40 MB · STT ~400 MB · speaker+face ~250 MB (lazy) · LLM 3B Q4 ~2.2 GB (on demand, unload on idle) · memory ~150 MB · TTS ~150 MB · headroom ~300 MB. On Pi 5 (8 GB) everything can stay resident.
