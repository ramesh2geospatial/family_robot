# FamilyRobot – Autonomous Build Bootstrap Prompt

Give this entire file as a single prompt to an agentic coding LLM (Antigravity / Gemini Flash, etc.) on the build machine. It will build FamilyRobot end-to-end, step by step, and can resume if interrupted or out of tokens.

## YOUR MISSION
Build the FamilyRobot platform: a low-cost, voice-first, local-first family companion + home-automation assistant for an 8-member Indian family, running from one shared codebase across Desktop → Android → Raspberry Pi 5. Languages: English, Hindi, Marathi.

You are an autonomous builder. Work incrementally, test continuously, and persist progress so any future session can resume exactly where you left off.

## PREREQUISITES (SET UP ONCE ON A FRESH MACHINE)
- **OS**: Linux, macOS, or Windows + WSL2 (Ubuntu). Build the Desktop stage here.
- **Tools**: Git, Python 3.11, `pip`, `venv`; C/C++ build tools (for `llama-cpp-python`); optional Docker.
- **Network**: internet for first-time model + package downloads (then runs offline).
- **Create & activate a venv**, then install editable with the desktop extra (Step 1 generates `pyproject.toml`).
- **No secrets required** for the local-first Desktop build. Cloud keys are optional and only for opt-in features (put in `secrets.env`, never commit).
- If a required tool is missing, install it (or print the exact command) before proceeding.

## AUTHORITATIVE SPEC (READ FIRST, IN ORDER)
1. `AGENTS.md` - always-on rules & defaults (repo root)
2. `docs/rules/architecture.md` - layout & port interfaces
3. `docs/rules/tech-stack.md` - pinned deps & models
4. `docs/rules/skills-catalog.md` - skills & ACL
5. `docs/rules/implementation-plan.md` - Stage D0 + 14 ordered steps
6. `docs/rules/testing-strategy.md` - test suites & gates
7. `docs/rules/progress-ledger.md` - how to track/resume

## OPERATING LOOP (REPEAT UNTIL ALL STEPS COMPLETE)
1. **Load context**: read `BUILD_STATE.md` at repo root (a pre-filled copy ships with this repo). If absent, create it from the template in `progress-ledger.md`. Begin at Stage D0 (build harness), then Step 1.
2. **Pick the next step**: the first step whose status is `pending` or `in_progress` in `BUILD_STATE.md`.
3. **Announce**: write a one-line plan for this step into `BUILD_STATE.md` (status `in_progress`).
4. **Implement**: create/modify only the files listed for that step in `implementation-plan.md`.
5. **Test**: run the test gate for that step (see `testing-strategy.md`). Fix until green.
6. **Checkpoint**: update `BUILD_STATE.md` - mark step `done`, record files changed, test results, commit hash, and a 2-3 line summary. Append to the decision log.
7. **Commit**: `git add -A && git commit -m "step <N>: <summary>"`
8. **Repeat** from 1. Stop only when every step is `done` or a hard blocker is recorded.

## RESUMABILITY RULES (CRITICAL)
- `BUILD_STATE.md` is the single source of truth. Never rely on chat memory. Re-read it at the start of every session.
- Keep each step **small and atomic** so a checkpoint is never far away.
- After any step, the repo must be in a **"green, committed state"** (tests pass, nothing half-written).
- If you must stop mid-step, set status `in_progress`, write exactly what's left under "Next action", and commit what compiles. Never leave the build broken.
- Record every non-obvious decision in the **Decision Log** so future sessions keep the same assumptions.

## CONTEXT-AWARENESS RULES
- Before editing, re-read the relevant reference file section; do not guess interfaces.
- Respect the **"one rule"**: shared code in `packages/` (ports only), hardware code in `adapters/`.
- Honor **"defaults"**: local-first privacy, encrypted memory, ACL roles, mains-voltage safety, fail-safe power.
- Build order is **Desktop → Android → Pi**. Do not start a platform until the previous platform's Definition-of-Done passes (spec §2X.8).

## QUALITY GATES (MUST PASS BEFORE A STEP IS 'DONE')
- Unit tests for new code: green.
- Port contract tests for any new/changed adapter: green.
- Regression suite (all prior tests): green.
- Functional test for the step's user-visible behaviour: green.
- Lint/format clean (`ruff`, `black`).
- `BUILD_STATE.md` updated and committed.

## WHAT "DONE" MEANS (WHOLE PROJECT)
All three platform columns of spec §2X.8 pass from one shared codebase; privacy/safety/reliability defaults upheld; business acceptance tests (family scenarios) pass. See `testing-strategy.md` for the business test list.

## START NOW
Read the spec files, create/parse `BUILD_STATE.md`, and begin at the first `pending` step. Announce the step, implement, test, checkpoint, commit. Continue autonomously.
