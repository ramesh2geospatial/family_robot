# Spec Audit Protocol

This protocol guides the Council of Three model spec auditors to cross-check implementation behavior against specifications.

## 1. Safety and Access Control Audit (§5.3)
- **Check 1**: Does the main loop enforce identity matching (face + voice fusion) for high-voltage geyser / pump controls?
- **Check 2**: Does the Webapp companion endpoint block children and guests from executing geyser controls?

## 2. Power and Fail-Safe Audit (§5.5)
- **Check 3**: Does the Pi UPS monitoring system handle re-charging states without triggering power-cut safe-shutdown loops?

## 3. Cryptographic and Database Security (§5.1, §5.4)
- **Check 4**: Are database contents encrypted with SQLCipher on startup using keys from local config parameters?
- **Check 5**: Are update packages verified via signed public key checksums prior to extraction?
