# FamilyRobot BUILD STATE (single source of truth – read me first)

The autonomous builder (see [BUILD_PROMPT.md](BUILD_PROMPT.md)) updates this file after every step.
Resume rule: read this file first, find the first 'in_progress'/'pending' step, continue.

## CURRENT
- **Stage**: D2 Android
- **Active step**: 11
- **Status**: pending
- **Next action**: implement Android adapters
- **Repo green**: yes
- **Last commit**: (pending commit)

## STEP TRACKER
| # | Stage | Step | Status | Tests | Commit |
|---|---|---|---|---|---|
| 0 | D0 | Build harness (tests, ledger, lint) | done | smoke tests passed | a8cfbb2 |
| 1 | D1 | Project skeleton | done | cli help passes | a05ecc8 |
| 2 | D1 | Ports + config + wiring | done | unit tests passed | 577af91 |
| 3 | D1 | Desktop adapters | done | contract tests passed | 3e2091d |
| 4 | D1 | Perception (wake/STT/VAD) | done | unit tests passed | b1012d9 |
| 5 | D1 | Cognition + memory | done | 52 unit tests passed | (pending) |
| 6 | D1 | Expression + loop | done | 52 unit tests passed | (pending) |
| 7 | D1 | Governance (identity/ACL) | done | 29 unit tests passed | (pending) |
| 8 | D1 | First skills | done | 21 unit tests passed | (pending) |
| 9 | D1 | Companion PWA | done | 13 unit tests passed | (pending) |
| 10 | D1 | Dockerize (dev) | done | Dockerfile + compose created | (pending) |
| 11 | D2 | Android adapters | pending | - | - |
| 12 | D2 | Real network smart-home | pending | - | - |
| 13 | Pi | Pi adapters | pending | - | - |
| 14 | Pi | Harden & ship | pending | - | - |

## DEFINITION-OF-DONE MATRIX (SPEC §2X.8)
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

## DECISION LOG (APPEND-ONLY)
- (none yet)

## SESSION LOG (APPEND-ONLY)
- 2026-06-26 session: completed step 0 (build harness); pytest smoke test passes; linting/formatting verified.
- 2026-06-26 session: completed step 1 (project skeleton); CLI entrypoint verified; package structure configured.
- 2026-06-26 session: completed step 2 (ports + config + wiring); typing protocols created; Pydantic configuration loader and dynamic wiring logic implemented and unit tested.
- 2026-06-26 session: completed step 3 (desktop adapters); implemented PyAudio input/output, OpenCV VideoCapture webcam, and logging mock home/power/notify adapters; contract tests created and passed.
- 2026-06-26 session: completed step 4 (perception); implemented openWakeWord detector with ONNX fallback, Silero VADIterator, faster-whisper small STT, and unit tests.
- 2026-06-26 session: completed steps 5+6 (cognition+memory+expression+loop); implemented LlamaLLMClient (llama-cpp-python), MemoryStore (SQLite WAL + cosine fallback), IntentRouter (6 intents + LLM fallback), PiperTTSEngine (pyttsx3 fallback), ResponseFormatter, main orchestrator loop, and full entry point; 52 unit tests passed.
- 2026-06-26 session: completed steps 7+8 (governance+skills); implemented Role/FamilyMember/IdentityStore, ACL permission matrix (5 roles × 11 permissions with polite denials), AuditLog (JSON lines), BaseSkill/SkillRegistry framework, and 4 skills (lights, reminders, memory_admin, assistant with manifests); 103 total unit tests passed. Step 3 audit confirmed full compliance with original plan.
- 2026-06-27 session: completed steps 9+10 (PWA+Docker); FastAPI backend with REST endpoints (device control, enrollment, memory CRUD, status), PWA frontend (dark theme, tabbed UI, service worker), Dockerfile (python:3.11-slim-bookworm), docker-compose (web+mqtt+core), Mosquitto config; 116 total unit tests passed. Stage D1 Desktop complete.

