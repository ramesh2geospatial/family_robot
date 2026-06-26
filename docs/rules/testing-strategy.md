# FamilyRobot - Testing Strategy (unit · contract · regression · functional · business)

> Defines the test pyramid and the **gate** each build step must pass. Tests are first-class: no step is `done` until its gate is green and the full regression suite still passes.

## Tooling
- Runner: **pytest** (+ `pytest-asyncio`, `pytest-cov`).
- Lint/format: **ruff** + **black**. Type check: **mypy** (advisory).
- Layout: `tests/{unit,contracts,functional,business,regression}/`. Markers in `pyproject.toml`:
  `unit`, `contract`, `functional`, `business`, `slow`, `hardware`.
- Hardware-dependent tests use `@pytest.mark.hardware` and are **skipped** where the device is absent (so Desktop CI stays green; Pi CI runs them).

## 1. Unit tests (`tests/unit/`)
- Scope: one function/class in isolation; mock ports and external models.
- Examples: intent_router matches utterances; acl denies child+geyser; memory decay logic; config override merge.
- Gate: every new module ships unit tests; coverage target **≥ 80%** on `packages/`.

## 2. Contract tests (`tests/contracts/`)
- Scope: every **port** has one behavioural suite; **every adapter** (desktop/android/pi/mock) must pass it.
- Guarantees cross-platform reuse - an adapter is "done" only when it satisfies the identical contract.
- Example: `test_home_port` asserts `set_switch` then `get_state` reflects the change, for mock, wifi_plug, and gpio adapters.
- Gate: any new/changed adapter passes its port contract suite on its native arch.

## 3. Functional tests (`tests/functional/`)
- Scope: a full user-visible behaviour through the real pipeline, with models stubbed/small and ports mocked.
- Examples: "Hello Puppy → 'turn on the living room light'" results in HomePort.set_switch called + spoken confirmation; "remember milk on Sunday" then restart → recall returns it.
- Gate: the step's headline behaviour has a passing functional test.

## 4. Regression suite (`tests/regression/` + all prior)
- Scope: the **entire accumulated** unit+contract+functional set, run after every step.
- Catches breakage in previously-working features. Add a regression test whenever a bug is fixed.
- Gate: full suite green before a step is marked `done`.

## 5. Business / acceptance tests (`tests/business/`)
- Scope: real **family scenarios** mapped to the business requirements. Written as Given/When/Then.
- These define "the product works for the family." Run before declaring a phase complete.

### Business scenarios (Phase 1-2)
| ID | Given / When / Then |
|---|---|
| B1 | Given an enrolled parent, when they say "Hello Puppy, turn on the geyser", then it switches on and is logged. |
| B2 | Given an enrolled child, when they ask to turn on the water pump, then it is **refused** politely. |
| B3 | Given Hindi speech "light chalu karo", then the light turns on (multilingual). |
| B4 | Given Marathi speech "majha homework madhe madat kar", then homework help responds in Marathi. |
| B5 | Given "remember Aai's birthday is 12 Aug", when asked next session, then it recalls it (long-term memory across restart). |
| B6 | Given two enrolled members speaking, then speaker-ID attributes each correctly and personalizes the reply. |
| B7 | Given a cooking request, then step-by-step recipe is read with parallel timers set. |
| B8 | Given "play a song", then music plays from YouTube/local and "dance mode" scores moves (Phase 2). |
| B9 | Given no internet, then wake/STT/LLM/TTS/memory still work locally (offline-first). |
| B10 | Given a power cut (UPS), then the memory DB is intact after restart (no corruption). |
| B11 | Given cloud features are off, then no raw audio/video/memory leaves the device (privacy). |
| B12 | Given a guest, then no memory is written about them. |

## Per-step gate (enforced by BUILD loop)
A step is `done` only when:
1. New unit tests pass · 2. Contract tests pass (if adapter touched) · 3. Functional test for the step passes · 4. **Full regression** green · 5. Lint/format clean · 6. Relevant business scenarios pass (at phase boundaries).

## Phase gates (business acceptance)
- **\*End of D1 (Desktop):\*** B2, B3, B5, B9, B11, B12 pass (mock home).
- **\*End of D2 (Android):\*** B1, B3, B6 pass with a real Wi-Fi plug from the phone.
- **\*End of Pi Phase 2:\*** all B1-B12 pass on the Pi.

## CI (optional but recommended)
- GitHub Actions matrix: `{amd64 desktop, arm64}` × run `unit + contract(non-hardware) + functional + regression`.
- Hardware-marked tests run only on a self-hosted Pi runner.
- Build the multi-arch Docker image on green.
