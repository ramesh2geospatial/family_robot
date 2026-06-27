"""
Secure OTA Updater.
Handles signature verification, staged updates, backups, and rollback logic.
"""

import logging
import os
import shutil
import subprocess
import tarfile
from pathlib import Path

logger = logging.getLogger(__name__)


class OtaUpdater:
    """
    Manages secure software updates by verifying RSA/ECDSA signatures,
    applying updates in stages, and supporting rollback on failure.
    """

    def __init__(self, install_dir: str, backup_dir: str, public_key_path: str) -> None:
        self.install_dir = Path(install_dir)
        self.backup_dir = Path(backup_dir)
        self.public_key_path = Path(public_key_path)

    def verify_signature(self, archive_path: str, signature_path: str) -> bool:
        """
        Verify the signature of the update archive using the public key.
        Uses Python's cryptography package if available; falls back to openssl CLI.
        """
        archive = Path(archive_path)
        signature = Path(signature_path)

        if (
            not archive.exists()
            or not signature.exists()
            or not self.public_key_path.exists()
        ):
            logger.error("Missing archive, signature, or public key for verification.")
            return False

        # Attempt verification via cryptography library
        try:
            from cryptography.hazmat.primitives import hashes
            from cryptography.hazmat.primitives.asymmetric import padding
            from cryptography.hazmat.primitives.serialization import load_pem_public_key

            public_key_bytes = self.public_key_path.read_bytes()
            public_key = load_pem_public_key(public_key_bytes)

            archive_bytes = archive.read_bytes()
            signature_bytes = signature.read_bytes()

            # Verify signature (assuming standard RSA SHA256 signature)
            public_key.verify(
                signature_bytes, archive_bytes, padding.PKCS1v15(), hashes.SHA256()
            )
            logger.info("Signature verified successfully using cryptography library.")
            return True
        except ImportError:
            # Fallback to OpenSSL CLI (standard on Linux/Pi)
            logger.info("cryptography package not found; falling back to OpenSSL CLI.")
            try:
                # OpenSSL command to verify signature
                # openssl dgst -sha256 -verify <public_key>
                # -signature <signature> <archive>
                cmd = [
                    "openssl",
                    "dgst",
                    "-sha256",
                    "-verify",
                    str(self.public_key_path),
                    "-signature",
                    str(signature),
                    str(archive),
                ]
                res = subprocess.run(cmd, capture_output=True, check=False)
                if res.returncode == 0:
                    logger.info("Signature verified successfully using OpenSSL CLI.")
                    return True
                else:
                    err = res.stderr.decode().strip()
                    logger.error(f"OpenSSL CLI verification failed: {err}")
                    return False
            except Exception as e:
                logger.error(f"OpenSSL CLI verification failed to execute: {e}")
                return False
        except Exception as e:
            logger.error(f"Signature verification failed: {e}")
            return False

    def backup_current(self) -> bool:
        """Create a staged backup of the current installation."""
        try:
            if self.backup_dir.exists():
                shutil.rmtree(self.backup_dir)
            self.backup_dir.parent.mkdir(parents=True, exist_ok=True)
            shutil.copytree(self.install_dir, self.backup_dir, symlinks=True)
            logger.info(f"Staged backup created at {self.backup_dir}.")
            return True
        except Exception as e:
            logger.error(f"Failed to create backup: {e}")
            return False

    def apply_update(self, archive_path: str) -> bool:
        """Extract verified update archive, backing up first, and rollback

        if extraction fails.
        """
        if not self.backup_current():
            logger.error("Backup failed; aborting update to protect system.")
            return False

        try:
            with tarfile.open(archive_path, "r:gz") as tar:
                # Safe extraction (prevent directory traversal)
                def is_within_directory(directory, target):
                    abs_directory = os.path.abspath(directory)
                    abs_target = os.path.abspath(target)
                    prefix = os.path.commonpath([abs_directory, abs_target])
                    return prefix == abs_directory

                for member in tar.getmembers():
                    member_path = os.path.join(self.install_dir, member.name)
                    if not is_within_directory(self.install_dir, member_path):
                        raise Exception("Attempted Path Traversal in tar File")

                tar.extractall(path=self.install_dir)

            logger.info("Update archive extracted successfully.")
            return True
        except Exception as e:
            logger.error(f"Extraction failed: {e}. Initiating rollback...")
            self.rollback()
            return False

    def rollback(self) -> bool:
        """Roll back to the previous stable backup."""
        try:
            if not self.backup_dir.exists():
                logger.error("No backup found; cannot perform rollback.")
                return False
            if self.install_dir.exists():
                shutil.rmtree(self.install_dir)
            shutil.copytree(self.backup_dir, self.install_dir, symlinks=True)
            logger.info("Rollback completed successfully.")
            return True
        except Exception as e:
            logger.critical(f"FATAL: Rollback failed: {e}")
            return False
