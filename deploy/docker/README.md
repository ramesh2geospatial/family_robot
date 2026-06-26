# FamilyRobot Docker Deploy

## Quick Start

```bash
cd deploy/docker
docker compose up -d
```

Open **http://localhost:8080** (or `http://<your-ip>:8080` from a phone on the same Wi-Fi).

## Services

| Service | Port | Description |
|---------|------|-------------|
| `web`   | 8080 | Companion PWA (FastAPI + static) |
| `mqtt`  | 1883 | Eclipse Mosquitto MQTT broker |
| `mqtt`  | 9001 | MQTT WebSocket transport |

## Architecture

- **web** runs the FastAPI Companion PWA inside Docker
- **mqtt** provides the message broker for smart-home device communication
- **core** (voice loop) runs on the **host** because Docker containers typically can't access microphone/speaker hardware directly

To run the voice loop on the host:
```bash
python -m apps.familyrobot
```

## Multi-arch Build (for Pi deployment)

```bash
docker buildx build --platform linux/amd64,linux/arm64 -t familyrobot:latest .
```

## Volumes

| Volume | Purpose |
|--------|---------|
| `mqtt-data` | Mosquitto persistent messages |
| `mqtt-log` | Mosquitto logs |
| `app-data` | Memory DB, audit logs |
