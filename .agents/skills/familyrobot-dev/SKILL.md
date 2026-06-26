---
name: familyrobot-dev
description: 'Build and extend the FamilyRobot cross-platform family companion + home-automation assistant (Desktop -> Android -> Raspberry Pi). Use when adding a skill/feature, writing a platform adapter, wiring smart-home devices, handling voice/face/voice recognition, memory/RAG, or reviewing changes for cross-platform compatibility and privacy.'
argument-hint: '<what to build, e.g. "add a geyser smart-plug skill">'
---

# FamilyRobot Development (VS Code Copilot pointer)

> This project is **Antigravity-first**. The canonical, always-on rules live in **[AGENTS.md](../../AGENTS.md)** and the detailed rule docs in **`docs/rules/*`**. This skill simply points VS Code Copilot at them so both tools share one source of truth.

## Read these (canonical)
- Rules & defaults: [AGENTS.md](../../AGENTS.md)
- Architecture & port interfaces: [architecture.md](../../docs/rules/architecture.md)
- Tech stack & models: [tech-stack.md](../../docs/rules/tech-stack.md)
- Skills catalog & ACL: [skills-catalog.md](../../docs/rules/skills-catalog.md)
- Build plan (D0 + 14 steps): [implementation-plan.md](../../docs/rules/implementation-plan.md)
- Testing strategy: [testing-strategy.md](../../docs/rules/testing-strategy.md)
- Progress ledger & resume: [progress-ledger.md](../../docs/rules/progress-ledger.md)

## To build the whole project
Follow [BUILD_PROMPT.md](../../BUILD_PROMPT.md). Track progress in `BUILD_STATE.md`.
