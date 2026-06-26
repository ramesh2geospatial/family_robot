# AGENTS.md – FamilyRobot

Always-on instructions for the coding agent (Antigravity / Gemini Flash). Read this first, every session.

## What this project is
FamilyRobot – a low-cost, voice-first, local-first family companion + home-automation assistant for an 8-member Indian family (English, Hindi, Marathi). One shared codebase runs across Desktop → Android → Raspberry Pi 5.

## Read these before non-trivial work
1. `BUILD_PROMPT.md` – how to build the whole project autonomously (the operating loop).
2. `BUILD_STATE.md` – current progress; **single source of truth for resuming**.
3. `docs/specification.md` – architecture (§2X cross-platform), security, roadmap.
4. `docs/rules/` – detailed rules, port interfaces, tech stack, skills, testing, build steps.

## The one rule (non-negotiable)
**Compatible code is SHARED; only hardware-incompatible code is platform-specific.**
- Shared, device-agnostic logic → `packages/*` (depends on **port interfaces only**).
- Hardware/OS code → `adapters/{desktop,android,raspberrypi}` implementing a port.
- No shared module imports an adapter; platform is chosen by `config/<platform>.yaml`.

## Always-on defaults (verify in every change)
- **Local-first & private**: voice, vision, memory stay on-device. Cloud is opt-in per feature; **never** send raw memory.
- **Encrypted memory at rest**: (SQLCipher/LUKS); store embeddings, not raw photos/audio.
- **Security**: MQTT over TLS, IoT VLAN, signed updates, least privilege, no default passwords, validate all inputs.
- **Safety (mains)**: geyser/AC/pump/washer via certified smart plug or rated contactor – never a bare GPIO relay; keep hardware override + mic-mute.
- **Fail-safe**: survive power cuts (UPS + SQLite WAL); watchdog-restart workers.
- **ACL roles**: kids can't control geyser/pump/calls/purchases; guests write no memory.
- Build order is **Desktop → Android → Pi**; don't start a platform until the prior one's Definition-of-Done passes (spec §2X.8).

## How to work (resumable build)
- Follow the Operating Loop in `BUILD_PROMPT.md`: load `BUILD_STATE.md` → next step → implement → test → checkpoint → commit → repeat.
- After every step the repo must be **"green and committed"**. Never leave the build broken.
- Persist all progress and decisions in `BUILD_STATE.md` (not in chat memory).

## Quality gates (before any step is "done")
Unit + port-contract + regression + functional tests green; lint/format clean (`ruff`, `black`); `BUILD_STATE.md` updated and committed. Business scenarios pass at phase boundaries. See `docs/rules/testing-strategy.md`.

## To build everything
Open this repo in Antigravity and follow `BUILD_PROMPT.md`.
