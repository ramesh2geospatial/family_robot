#!/bin/bash
# Triage probes checking for ACL bypasses in main loop and webapp.

grep -q "check_intent" apps/familyrobot/main_loop.py
if [ $? -ne 0 ]; then
  echo "[FAIL] Orchestrator main loop does not call ACL validation check."
else
  echo "[PASS] Orchestrator main loop references check_intent."
fi

grep -q "check_permission" packages/core/webapp/app.py
if [ $? -ne 0 ]; then
  echo "[FAIL] FastAPI webapp does not call ACL validation check."
else
  echo "[PASS] FastAPI webapp references check_permission."
fi
