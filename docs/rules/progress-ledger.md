# FamilyRobot – Progress Ledger & Resume Protocol

> Defines `BUILD_STATE.md` (repo root) – the durable memory that lets an agent resume after interruption or token exhaustion. The agent reads/writes this file every session.

## Why
Chat context is volatile; tokens run out; sessions get interrupted.
`BUILD_STATE.md` is the **persistent, version-controlled** source of truth for what is built, what passed, and what's next. It is committed after every step.

## Rules
1. **Read `BUILD_STATE.md` first** in every session. If missing, create it from the template below.
2. **One step `in_progress` at a time.** Mark `done` only when its quality gate passes and changes are committed.
3. **Always leave green:** never end a session with broken/uncommitted-but-half-done code. If stopping mid-step, write "Next action" precisely.
4. **Append, don't overwrite** the Decision Log and Session Log – history matters for context continuity.
5. Keep entries terse. This file is loaded at the start of every session, so brevity preserves context budget.

## `BUILD_STATE.md` Template (create at repo root)
```markdown
# FamilyRobot BUILD STATE (single source of truth - read me first)

## Current
- Stage: D1 Desktop
- Active step: 1
- Status: pending
- Next action: scaffold monorepo + pyproject + .gitignore
- Repo green: yes
- Last commit: <none>

## Step Tracker
| # | Stage | Step | Status | Tests | Commit |
|---|---|---|---|---|---|
| 0 | D0 | Build harness (tests, ledger, lint) | pending | - | - |
| 1 | D1 | Project skeleton | pending | - | - |
| 2 | D1 | Ports + config + wiring | pending | - | - |
| 3 | D1 | Desktop adapters | pending | - | - |
| 4 | D1 | Perception (wake/STT/VAD) | pending | - | - |
| 5 | D1 | Cognition + memory | pending | - | - |
| 6 | D1 | Expression + loop | pending | - | - |
| 7 | D1 | Governance (identity/ACL) | pending | - | - |
| 8 | D1 | First skills | pending | - | - |
| 9 | D1 | Companion PWA | pending | - | - |
| 10 | D1 | Dockerize (dev) | pending | - | - |
| 11 | D2 | Android adapters | pending | - | - |
| 12 | D2 | Real network smart-home | pending | - | - |
| 13 | Pi | Pi adapters | pending | - | - |
| 14 | Pi | Harden & ship | pending | - | - |

## Definition-of-Done Matrix (spec §2X.8) - mark as platforms complete
| Capability | Desktop | Android | Pi |
|---|---|---|---|
| Wake "Hello Puppy" | [ ] | [ ] | [ ] |
| AEC + barge-in | [ ] | [ ] | [ ] |
| STT->LLM->TTS (en/hi/mr) | [ ] | [ ] | [ ] |
| Enroll face+voice | [ ] | [ ] | [ ] |
| Memory persists restart | [ ] | [ ] | [ ] |
| Smart-home command | [ ] | [ ] | [ ] |
| PWA reachable from phone | [ ] | [ ] | [ ] |
| Contract tests pass | [ ] | [ ] | [ ] |

## Decision Log (append-only; keep assumptions stable)
- <date> Step <N>: <decision and why>

## Session Log (append-only)
- <date> session: completed steps X-Y; tests green; next: step Z.

## Blockers (if any)
- <date>: <blocker, what was tried, what's needed>

## Status values
`pending` -> not started · `in_progress` -> being built now · `done` -> gate passed + committed · `blocked` -> needs external input (recorded in Blockers).

## Resume procedure (start of every session)
1. `git pull` (if remote) and read `BUILD_STATE.md`.
2. Find the first `in_progress` step (resume it) or first `pending` step (start it).
3. Re-read that step in `implementation-plan.md` and the referenced spec sections.
4. Continue the Operating Loop from `BUILD_PROMPT.md`.

## Interruption procedure (token/time runs out)
1. Stop at the nearest safe sub-point.
2. Ensure the repo compiles; commit what's safe.
3. Set the step `in_progress`, write precise "Next action".
4. Append a Session Log line. Done – next session resumes cleanly.
```
