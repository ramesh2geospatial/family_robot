# FamilyRobot BUILD STATE (single source of truth – read me first)

The autonomous builder (see [BUILD_PROMPT.md](BUILD_PROMPT.md)) updates this file after every step.
Resume rule: read this file first, find the first 'in_progress'/'pending' step, continue.

## CURRENT
- **Stage**: D1 Desktop
- **Active step**: 3
- **Status**: pending
- **Next action**: implement desktop adapters (Step 3)
- **Repo green**: yes
- **Last commit**: 577af91

## STEP TRACKER
| # | Stage | Step | Status | Tests | Commit |
|---|---|---|---|---|---|
| 0 | D0 | Build harness (tests, ledger, lint) | done | smoke tests passed | a8cfbb2 |
| 1 | D1 | Project skeleton | done | cli help passes | a05ecc8 |
| 2 | D1 | Ports + config + wiring | done | unit tests passed | 577af91 |
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
