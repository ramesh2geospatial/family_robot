# Integration Test Protocol

This protocol outlines the execution steps to verify end-to-end integration between PWA, core orchestrator, and smart-home components.

## 1. PWA Command to Home Adapter Integration
- **Step 1**: Start PWA API server:
  ```bash
  python -m apps.familyrobot --platform desktop --config config/desktop.yaml
  ```
- **Step 2**: Submit HTTP POST command to `/api/device/command`:
  ```bash
  curl -X POST http://localhost:8000/api/device/command -H "Content-Type: application/json" -d '{"device_id": "light", "action": "on"}'
  ```
- **Step 3**: Verify mock home adapter logs `set_switch` call and state changes to True.

## 2. Voice Pipeline Integration (Wake -> VAD -> STT)
- **Step 1**: Run the orchestrator voice main loop.
- **Step 2**: Speak "Hello Puppy." Verify wake word detection triggers VAD speech accumulation.
- **Step 3**: Speak a command. Verify text is transcribed and routed.
