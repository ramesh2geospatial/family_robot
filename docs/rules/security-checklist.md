# Security & Hardening Checklist (Spec §5/§10 Audit)

This document lists all security and privacy controls implemented for the FamilyRobot platform on the Raspberry Pi 5.

## 1. Data Protection at Rest (§5.1)
- **Database Encryption**: Implemented SQLCipher support inside `MemoryStore` (`packages/core/memory/memory_store.py`). When the `DB_ENCRYPTION_KEY` environment variable is set, connections are opened using `sqlcipher3` or `pysqlcipher3` and keys are derived immediately using `PRAGMA key` before any database query. Standard `sqlite3` fallback is preserved for local development testing.
- **Privacy First**: No raw audio, video, or photos are stored long-term. Only derived face/voice feature vectors (embeddings) are saved inside the database.

## 2. Software Supply Chain & Updates (§5.4)
- **Signed OTA Updates**: Implemented cryptographically verified software updates inside `OtaUpdater` (`packages/core/governance/updater.py`).
- **Signature Checking**: Updates are distributed as `.tar.gz` files alongside a `.sig` signature file. The signature is checked against a local trusted PEM public key using the Python `cryptography` module or standard system `openssl dgst -sha256 -verify`.
- **Staged Rollback**: The updater backs up the current installation before extracting the update. In the event of a directory traversal detection or extraction error, it automatically triggers a rollback to restore the previous stable backup.
- **Secrets Management**: Credentials (MQTT tokens, passwords, database keys) are stored in `secrets.env` (configured as `chmod 600`), and never checked into Git.

## 3. Network Isolation (§5.2)
- **Subnet Rules**: Implemented firewall configuration in `deploy/raspberrypi/nftables.conf`.
- **Isolation Policy**: Default-deny inbound rules. Incoming connections to SSH, HTTP (Web PWA), and MQTT ports are only accepted if originating from the local home network / guest VLAN (e.g. `192.168.0.0/16`) or trusted VPN subnets (Tailscale `100.64.0.0/10`). All other traffic is dropped.
- **TLS Protocol**: MQTT runs exclusively over TLS port `8883` with per-device ACL tokens.

## 4. Physical Safety & Controls (§5.5)
- **Hardware Mic-Mute**: The physical microphone array power line is routed through a mechanical latching switch with a red LED indicator. When muted, no current reaches the mic, ensuring physical-layer security.
- **Appliance Relay Override**: To prevent lockouts due to computer crashes or power cycles, all critical high-voltage contactors (geyser, water pump) are wired in parallel with a physical manual bypass switch.
