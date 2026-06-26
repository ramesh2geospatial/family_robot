# Family Companion Robot - Project Brief & Master Prompt (v2)

## 1. Project Vision
Design and build a low-cost, voice-driven **family companion + home-automation assistant** that is **platform-compatible across Desktop, Android phone, and Raspberry Pi** (developed in that order), and behaves like a friendly household member for an **8-member Indian family**. The **chosen production brain is the Raspberry Pi 5 (8 GB)**; the same code also runs on a desktop (development) and a spare Android phone (satellite or all-wireless brain).

It should:
- Recognize each family member by **face _and_ voice**.
- Hold natural conversations in **English, Hindi, and Marathi** (code-mixed "Hinglish" / "Minglish" too).
- Build **long-term memory** about the family (preferences, schedules, important dates, kids' study topics) and reuse that context in future chats.
- Control **all common Indian household appliances** - lights, fans, water pump, geyser, washing machine, mixer, AC, TV, etc.
- Play music, help with **dance practice, cooking recipes, homework doubts**, reminders and general Q&A.
- Behave like **Amazon Alexa / Google Nest Hub**, but **family-personalized, local-first, and privacy-respecting**.

---

## 2. Hardware Constraints & Recommendations

### 2.1 Compute
- **Chosen production brain:** **Raspberry Pi 5 (8 GB)**, 64-bit Raspberry Pi OS (Bookworm).
- **Also supported (same codebase):** Desktop/laptop (development, Docker/WSL2) and a spare **Android phone** (Termux - satellite or all-wireless brain).
- **Lean budget alternative:** Raspberry Pi 4 (4 GB) with staged model loading.
- **Alternative SBCs:** Orange Pi 5 (RK3588 NPU), Jetson Orin Nano (premium vision) - see §15.

### 2.2 Storage
- 128 GB high-endurance microSD **or** USB 3 SSD (recommended for LLM model loading and SQLite memory DB).

### 2.3 Audio I/O
- **Far-field mic:** ReSpeaker 4-Mic Array or 2-Mic HAT (better than a single USB mic in a noisy Indian kitchen/living room).
- **Speaker:** Small powered 5 W speaker over 3.5 mm or USB; or a Bluetooth speaker.

### 2.4 Vision
- Raspberry Pi Camera Module 3 (wide) - used **on demand**, not 24x7, for face recognition during enrollment and greetings.

### 2.5 Smart-home I/O (India-friendly)
- **GPIO 4-8 channel relay board** (with optocoupler isolation) for hard-wired control of bulbs, fans, pump.
- **Wi-Fi smart plugs** (Wipro, Syska, TP-Link Tapo, Mi) flashed with Tasmota/ESPHome **or** controlled via Tuya cloud / Home Assistant integration. Best for **AC, geyser, washing machine, TV** (mains-voltage / certified appliance).
- **IR blaster** (USB IR or ESP-based Tasmota IR) for legacy TV / AC / set-top box.
- **MQTT broker** (Mosquitto on the Pi) as the central message bus.

### 2.6 USB / OTG
- Pi 5 already exposes USB ports (or Pi 4 exposes 4x USB-A ports). Add a **powered USB hub** for: USB mic, IR blaster, optional USB DAC, USB drive, Zigbee/Z-Wave dongle (future).
- If using a Pi Zero 2 W as a satellite, its **micro-USB OTG** can host a single device (mic _or_ Wi-Fi dongle).

### 2.7 Power
- 5 V / 3 A USB-C supply (5V / 5A recommended for Pi 5).
- **UPS HAT (e.g., Waveshare UPS HAT C)** strongly recommended - Indian power cuts must not corrupt the memory DB.

### 2.8 Form Factor (India-specific recommendation)
- Recommended primary build: **stationary tabletop "smart speaker" unit** placed in the **living room / dining area** where the whole family gathers.
- **Enclosure:** Wood + 3D-printed front grille, ~15 x 15 x 20 cm.
- **Look:** Cloth-covered front (Alexa-style), small OLED/round LCD for expressions and clock, soft RGB ring for listening/speaking state.
- **Mounting:** Rubber feet for tabletop; optional wall mount near the puja / TV unit.
- **Why not mobile/wheeled?** Indian homes have thresholds, rugs, kids, and pets - a wheeled bot is fragile and overkill for v1. Keep mobility as a Phase 3 stretch goal.
- **Satellite units (Phase 2):** Small Pi Zero 2 W + mic in kitchen and bedrooms, all talking to the main Pi 5 (or Pi 4) over MQTT, so the assistant is reachable everywhere.

---

## 3. Core Capabilities (MVP - Phase 1)

1. **Wake-word detection** - always-on, offline. Custom wake word (e.g., "Hello Ghar" / "Suno") via **openWakeWord** or **Porcupine**. (Final selected wake word: "Hello Puppy").
2. **Speech-to-text (STT)** - multilingual (en / hi / mr):
   - On-device: **whisper.cpp 'small' (Q5)** or **Vosk** Hindi + English models.
   - Cloud fallback: Azure / Google STT when accuracy matters (opt-in).
3. **Speaker (voice) recognition** - identify _who_ is talking using **Resemblyzer** or **SpeechBrain ECAPA-TDNN** embeddings; combined with face recognition for high confidence.
4. **Face recognition** - `face_recognition` (dlib) or **InsightFace** lite; enroll all 8 family members once.
5. **Conversation engine** - small local LLM (Phi-3-mini, Llama 3.2 3B, Qwen2.5 3B) via **\`llama.cpp\` Q4_K_M**; auto-switch to **cloud LLM (OpenAI / Gemini / Groq)** when internet is up and the query is complex.
6. **Long-term family memory** - see Section 5.
7. **Text-to-speech (TTS)** - **Piper TTS** voices for English + Hindi + Marathi; cloud TTS (Azure Neural / ElevenLabs) optional for richer voice.
8. **Home automation skills** - toggle/dim lights, fan speed, switch geyser, water pump, AC on/off, TV via IR, washing machine plug.
9. **Daily-life skills** - alarms, reminders, timers (cooking!), weather, news headlines, calendar, shopping list, unit/currency conversion.
10. **Entertainment** - play music (local library + YouTube Music / Spotify / Saavn via APIs), play stories for kids, "dance mode" (play song + count beats / mirror moves via camera - see Section 4).
11. **Cooking helper** - read recipes step-by-step in Hindi/Marathi, set parallel timers, convert measurements (cup <-> grams), suggest substitutes.
12. **Homework / doubts helper** - explain concepts at the child's grade level, solve math step-by-step, quiz mode.
13. **Privacy-first** - all audio/video processed locally by default; cloud calls require explicit opt-in per feature; an obvious **mute button** cuts mic power.

---

## 4. Stretch Goals (Phase 2+)

- **Dance coach** - camera-based pose detection (MediaPipe Pose) to score moves and give feedback; pick songs by mood/tempo.
- **Cooking vision** - camera looks at the stove/ingredients and gives suggestions.
- **Mobile app / web dashboard** (PWA) for config, manual control, and memory editing.
- **Calendar & to-do** (Google / CalDAV) sync.
- **Security mode** - notify phone if unknown face is detected at night.
- **Energy monitoring** of controlled appliances.
- **OLED face / emotions** with simple expressions.
- **Home Assistant satellite** integration (Wyoming protocol) so it plugs into an existing HA setup.
- **Mobile/wheeled body** (Phase 3) for follow-me reminders.

---

## 5. Long-Term Family Memory (key differentiator)

### 5.1 What it remembers
- **Per-person profile:** name, relation, DOB, language preference, voice/face embedding, favorite songs/foods, allergies, school/work schedule.
- **Episodic memory:** "Aai asked to remind buying milk on Sunday", "Dada's exam is on 12th", "Pump was switched on at 6:15 am".
- **Semantic memory:** family rules, recurring routines (puja time, school bus time), household inventory.
- **Conversation history:** summarized rolling context per user.

### 5.2 How it's stored (local-first)
- **SQLite** for structured data (`family.db`).
- **Vector store** (Chroma / SQLite-VSS / FAISS) for embeddings of past chats and notes, enabling **RAG** so the LLM can "recall" relevant memories.
- **Encrypted at rest** (SQLCipher or filesystem-level LUKS) - the DB contains personal data.
- **Hourly snapshot** to USB SSD / optional encrypted backup to user's own cloud (Google Drive / OneDrive) - opt-in.

### 5.3 Memory lifecycle
- **Write:** every skill can log a memory item with tags `{user, type, ttl}`.
- **Decay:** low-value items auto-expire (e.g., one-off timers).
- **Review:** weekly summary spoken to the family ("Here's what I remembered this week - keep or forget?").
- **Right-to-forget:** any user can say "forget that" / "delete my data" and the bot purges.

---

## 6. Software Architecture

```
+-------------------------------------------------------------------------------+
|                      Family Robot (Raspberry Pi 4 / 5, 8 GB)                  |
|                                                                               |
|    [Mic Array] -> Wake Word -> VAD -> STT (multi-lang)                        |
|                                      |                                        |
|                                Speaker-ID + Face-ID -> User context           |
|                                      |                                        |
|                                 Intent Router                                 |
|                                /     |       \                                |
|                  Skill Plugins  Local LLM   Cloud LLM (opt-in)                |
|                  - lights       (Q4 3B)     - OpenAI/Gemini/Groq              |
|                  - fan/AC         \            /                              |
|                  - pump/geyser   Long-Term Memory (SQLite + Vector)           |
|                  - music/dance            |                                   |
|                  - cooking                |                                   |
|                  - homework               v                                   |
|                  - reminders      TTS (Piper / cloud) -> [Speaker]            |
|                                                                               |
|    [Camera] -> Face Recognition (on demand)                                   |
|                                                                               |
|    MQTT bus   <----> Relays / Smart Plugs / IR Blaster / Satellites           |
+-------------------------------------------------------------------------------+
```

- **Language:** Python 3.11 + C/C++ via `llama.cpp` / `whisper.cpp`.
- **Process model:** asyncio supervisor + **separate worker processes** for STT, LLM, vision so a crash in one doesn't kill audio I/O.
- **Config:** `config.yaml` (devices, family profiles, language, feature toggles) + `secrets.env`.
- **Logging:** rotating local logs; **no audio/video persisted** unless explicitly enabled for debugging.
- **OTA updates:** `git pull` + systemd unit restart, gated by a signed manifest.

---

## 7. Resource Budget (Raspberry Pi 4 / 5, 4 GB)

| Component | Approx. RAM | Notes |
|---|---|---|
| OS + services + MQTT | ~450 MB | Headless Pi OS Lite, Mosquitto |
| Wake word | ~30 MB | openWakeWord / Porcupine |
| STT (whisper.cpp small) | ~400 MB | or Vosk en+hi small ~250 MB |
| Speaker-ID + Face-ID | ~250 MB | lazy-loaded |
| Local LLM (3B Q4) | ~2.2 GB | Phi-3-mini / Llama 3.2 3B / Qwen 2.5 3B |
| Memory (SQLite + vec) | ~150 MB | grows slowly |
| TTS (Piper) | ~150 MB | loaded on demand |
| Headroom | ~350 MB | skills, buffers |

> If 4 GB is too tight with all features on, default to **cloud LLM** (internet is available at this home) and keep STT/TTS/vision/memory **local**. This gives Alexa-class responsiveness without sacrificing privacy of the memory store.

---

## 8. Family & Personalization Plan (8 members)

- **Enrollment app** (CLI + small web page): record 3-5 voice samples + 5-10 face photos per member, capture name/relation/language/DOB/preferences.
- **Per-user wake response:** "Hi Aai, good morning" vs. "Hey Rohan, school bus in 20 minutes".
- **Role-based permissions:** kids cannot turn on geyser/pump or order things online; parents can.
- **Quiet hours** per user (no notifications during study/sleep).

---

## 9. Safety (mains-voltage appliances)

- **Never switch geyser, AC, washing machine, water pump directly from a hobby relay** without proper enclosure, fusing, and rating.
- **Prefer certified BIS-marked smart plugs** (Wipro / Syska / TP-Link Tapo) for any 6 A+ load; control them via Wi-Fi/MQTT.
- **For hard-wired switching, use contactors** rated for the load, driven by the relay; install in a metal enclosure by a licensed electrician.
- **Water pump:** add **dry-run protection** and a hardware override switch - the bot is convenience, not a single point of failure.

---

## 10. Privacy & Security Checklist

- Local-first defaults; cloud is opt-in per feature and per user.
- Mic mute is a **hardware switch**, not just software.
- Encrypt `family.db` at rest; rotate keys.
- No raw audio/video leaves the device unless the user explicitly enables a cloud STT/LLM.
- Signed OTA updates; auto-security-patch the OS.
- Guest mode for visitors (no memory written).

---

## 11. Deliverables Requested from the AI/Engineer

1. **Bill of Materials (BOM)** with India links (Amazon.in / Robu.in / Robocraze) and approx. prices in INR.
2. **Phased build plan** (Phase 1 MVP -> Phase 3 stretch).
3. **Pinned software stack** with model filenames/sizes that fit 4 GB.
4. **Python project layout** with packages:
   - `wakeword/`, `stt/`, `tts/`, `llm/`, `memory/`, `vision/`, `audio/`,
   - `skills/{lights,fan,ac,pump,geyser,music,dance,cooking,homework,reminders,...}`,
   - `home/{gpio,mqtt,ir,plugs}`, `app/` (supervisor), `enroll/`, `config.yaml`.
5. **Starter code** for:
   - Wake-word -> STT -> speaker-ID -> memory-aware LLM -> TTS pipeline.
   - One GPIO relay skill (toggle a light).
   - One MQTT smart-plug skill (geyser on/off).
   - Family enrollment script (face + voice).
   - Memory read/write with RAG.
6. **Safety guidance** wiring diagram for relay + contactor for the water pump and geyser.
7. **Privacy/security checklist** implemented as defaults in `config.yaml`.

---

## 12. Constraints & Preferences

- Budget-friendly, mostly open-source.
- Offline-first for sensitive paths (memory, mic, vision); cloud for heavy LLM only.
- Easy for non-technical family members - wake word + natural speech in Hindi / Marathi / English, no app required for daily use.
- Maintainable by a single developer in spare time.
- Must respect Indian power-cut reality (UPS HAT, auto-resume, no data loss).

---

## 13. Locked-in Decisions (from user)

- **Languages:** English, Hindi, Marathi (with code-mixing support).
- **Family size:** **8 members**, all to be enrolled (face + voice).
- **Appliances:** all common domestic appliances (lights, fans, AC, geyser, pump, washing machine, TV, mixer, etc.).
- **Internet:** available - cloud fallback is allowed but **opt-in and never for raw memory**.
- **Form factor:** **stationary tabletop smart-speaker unit** for the living/dining area; satellite mics in kitchen/bedrooms in Phase 2.
- **Memory:** long-term, local, encrypted SQLite + vector store; RAG-backed personalization.
- **Persona:** **Alexa-class** household assistant - music, cooking, dance, homework, smart-home, reminders, conversation.
- **Wake word:** **"Hello Puppy"** (custom-trained via openWakeWord).
- **Existing devices:** only **Android phones** in the family - used as Wi-Fi companions / remotes. **No** existing smart plugs, IR blasters, Alexa, Google Home, or Home Assistant - everything else will be purchased.
- **No third-party voice-assistant subscription** (no Alexa / Google Assistant subscription). Build **Alexa-equivalent functionality from scratch** using open-source components.
- **Phone calls + WhatsApp:** Phase 2 - robot can place voice calls / send WhatsApp messages **only to enrolled family members** (whitelist), triggered by voice with confirmation. **Routed through the family's Android phone** (free, uses your existing number) via an Android companion service - no paid gateway.
- **Companion Android app:** lightweight PWA / native app served from the Pi over Wi-Fi for setup, manual control, memory review, and push notifications.
- **Budget tier:** **Recommended** (full Alexa-class build) - see BOM.
- **Music sources:** **YouTube Music / YouTube** + **local MP3 library** (no Spotify/Saavn needed).
- **Compute board:** **Raspberry Pi 5 (8 GB)** chosen for the Recommended build (best support + headroom for local AI). See Section 15 for evaluated alternatives.
- **Enclosure:** **both** - a clean tabletop "smart-speaker" version **and** a kid-friendly **puppy-shaped** body (matching the "Hello Puppy" wake word). Shared internals, two swappable shells.

---

## 14. Companion Android App (Phase 1)

Since the only existing device is an Android phone, the Pi will host a small **local web app (PWA)** reachable over home Wi-Fi at `http://familyrobot.local`:
- Enroll family members (face photos + voice samples) using the phone camera/mic.
- Manual on/off of lights, fan, pump, geyser, AC, etc.
- View / edit long-term memory entries.
- Push notifications (via local Wi-Fi + ntfy.sh self-hosted or simple WebPush) for reminders, alerts, unknown-face events.
- Phase 2: trigger WhatsApp / phone-call skills with confirmation.

No Android app store publishing required - just "Add to Home Screen" from Chrome.

---

## 15. Compute Board - Raspberry Pi vs Alternatives

The project is **not locked to Raspberry Pi**. The software stack runs on any 64-bit ARM/x86 Linux SBC. Evaluated options (India, mid-2026):

| Board | RAM | AI accel | Approx ₹ | Verdict |
|---|---|---|---|---|
| **Raspberry Pi 5 (8 GB)** ☑ chosen | 8 GB | CPU only | ~9,000 | Best ecosystem, docs, HATs; runs local 3B LLM comfortably |
| Raspberry Pi 4 (4 GB) | 4 GB | CPU only | ~5,500 | Lean budget; stage models carefully |
| **Orange Pi 5 / 5 Plus (RK3588)** | 8-16 GB | **6 TOPS NPU** | ~9,000-14,000 | Best value AI performance; rougher software |
| Radxa Rock 5B (RK3588) | 8-16 GB | 6 TOPS NPU | ~12,000+ | Strong, enthusiast support |
| Khadas VIM3/VIM4 | 4-8 GB | NPU | ~13,000+ | Compact AI, premium |
| **NVIDIA Jetson Orin Nano** | 8 GB | **GPU/CUDA** | ~35,000+ | Best for heavy real-time vision/LLM; pricey, higher power |
| Le Potato / Banana Pi | 2-4 GB | weak | ~3,500 | Too weak - avoid |

**Decision:** **Raspberry Pi 5 (8 GB)** - best balance of cost, support, accessories, and local-AI headroom. Orange Pi 5 is the value alternative if more NPU muscle is wanted later; Jetson Orin Nano is the premium upgrade for vision-heavy dance/security features.

---

## 16. Budget Quote (Recommended build - INR, mid-2026 estimates)

Full line items and India buying links are in [hardware/BOM.md](../hardware/BOM.md). Recommended-tier total: **~₹33,000-36,000** one-time, **~₹50/month** recurring (electricity only).

### Phase 2 add-ons (optional, when expanding)

| Item | Approx. Cost (INR) |
|---|---|
| 2x Pi Zero 2 W satellite kits (kitchen + bedroom) | 6,000 |
| 4x extra smart plugs | 4,800 |
| Smart bulbs (4x WiFi RGB) | 3,200 |
| Zigbee USB dongle + 4 Zigbee switches | 6,200 |
| **Phase 2 subtotal** | **~20,200** |

### Software/cloud (recurring)

| Item | Cost |
|---|---|
| OS, Mosquitto, Python stack, llama.cpp, whisper.cpp, Piper TTS, Vosk, MediaPipe, SQLite | **Free (open-source)** |
| Optional cloud LLM (OpenAI/Gemini/Groq) usage | ~0-300 INR/month typical for a family (opt-in, cached) |
| Optional cloud STT (Azure/Google) heavy use | ~0-200 INR/month (opt-in) |
| Music (YouTube + local MP3 library) | Free (uses existing YouTube/YouTube Music access) |
| WhatsApp / phone-call via family Android phone | Free (uses existing mobile plan, no extra gateway costs) |
| **Mandatory recurring** | **INR 0 (completely free without opt-in cloud features)** |

---

## 17. All Major Decisions - Locked

| Topic | Decision |
|---|---|
| Compute board | Raspberry Pi 5 (8 GB) |
| Budget tier | Recommended (~INR 33,000-36,000) |
| Languages | English, Hindi, Marathi (+ code-mix) |
| Family | 8 members, face+voice enrolled |
| Appliances | All common domestic (lights, fan, AC, geyser, pump, washer, TV, mixer) |
| Music | YouTube/YouTube Music + local MP3 |
| WhatsApp/calls | Via family Android phone (free), family whitelist only |
| Companion app | PWA on phone over Wi-Fi |
| Enclosure | Both - tabletop smart-speaker + puppy-shaped shell (shared internals) |
| Memory | Local encrypted SQLite + vector RAG |
| Internet/cloud | Available; cloud AI opt-in, memory stays local |
| Wake word | "Hello Puppy" |

---

## 18. Development Approach - Desktop -> Android -> Raspberry Pi (Modular & Reusable)

Development proceeds across **three targets in order**, writing each capability **once** and reusing it everywhere:

1. **Desktop/laptop (Docker/WSL2, ₹0):** Build all **shared modules** (orchestrator, skills, memory, LLM, STT/TTS, PWA) plus a **desktop adapter** (laptop mic/webcam, **mock** smart-home). Test via laptop and phone browser.
2. **Android phone (Termux, ₹0):** Add only an **Android adapter** (phone mic/camera, Wi-Fi/ESP smart-home - no GPIO). **All shared modules are reused unchanged.** Docker isn't used on Android; the same Python code runs under Termux + proot Debian.
3. **Raspberry Pi 5:** Add only a **Pi adapter** (HAT mic, CSI camera, GPIO relays, UPS). Again **all shared modules are reused unchanged**; deploy the same image.

**Design rule (ports & adapters):** The shared core depends only on **interfaces** (AudioPort, CameraPort, HomePort, ...). **Compatible modules are shared** in `packages/*`; **incompatible, hardware-specific modules are built separately** in `adapters/{desktop,android,raspberrypi}`. Switching platform = swap the adapter via config, no change to shared code. Full module-by-module breakdown in [docs/specification.md](../docs/specification.md) §2X.
