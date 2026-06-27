"""
Unit tests for the secure OtaUpdater governance component.
"""

import io
import tarfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from packages.core.governance.updater import OtaUpdater


@pytest.mark.unit
class TestOtaUpdater:

    @pytest.fixture
    def setup_dirs(self, tmp_path: Path):
        install_dir = tmp_path / "install"
        backup_dir = tmp_path / "backup"
        public_key_path = tmp_path / "public_key.pem"

        install_dir.mkdir()
        public_key_path.write_text(
            "-----BEGIN PUBLIC KEY-----\nMOCKKEY\n-----END PUBLIC KEY-----"
        )

        # Write some files to install
        (install_dir / "app.py").write_text("print('version 1')")
        (install_dir / "utils.py").write_text("def run(): pass")

        return install_dir, backup_dir, public_key_path

    def test_backup_current(self, setup_dirs) -> None:
        install_dir, backup_dir, public_key_path = setup_dirs
        updater = OtaUpdater(str(install_dir), str(backup_dir), str(public_key_path))

        success = updater.backup_current()
        assert success is True
        assert backup_dir.exists()
        assert (backup_dir / "app.py").read_text() == "print('version 1')"
        assert (backup_dir / "utils.py").read_text() == "def run(): pass"

    def test_verify_signature_openssl_success(self, setup_dirs) -> None:
        install_dir, backup_dir, public_key_path = setup_dirs
        updater = OtaUpdater(str(install_dir), str(backup_dir), str(public_key_path))

        archive = install_dir.parent / "update.tar.gz"
        signature = install_dir.parent / "update.tar.gz.sig"
        archive.write_text("archive content")
        signature.write_text("signature content")

        mock_res = MagicMock()
        mock_res.returncode = 0

        # Simulate cryptography package is missing to force OpenSSL CLI path
        with (
            patch(
                "builtins.__import__",
                side_effect=ImportError("No module named cryptography"),
            ),
            patch("subprocess.run", return_value=mock_res) as mock_run,
        ):
            success = updater.verify_signature(str(archive), str(signature))
            assert success is True
            mock_run.assert_called_once()
            args = mock_run.call_args[0][0]
            assert "openssl" in args
            assert "-verify" in args

    def test_verify_signature_openssl_failure(self, setup_dirs) -> None:
        install_dir, backup_dir, public_key_path = setup_dirs
        updater = OtaUpdater(str(install_dir), str(backup_dir), str(public_key_path))

        archive = install_dir.parent / "update.tar.gz"
        signature = install_dir.parent / "update.tar.gz.sig"
        archive.write_text("archive content")
        signature.write_text("signature content")

        mock_res = MagicMock()
        mock_res.returncode = 1
        mock_res.stderr = b"Verification Failure"

        with (
            patch(
                "builtins.__import__",
                side_effect=ImportError("No module named cryptography"),
            ),
            patch("subprocess.run", return_value=mock_res),
        ):
            success = updater.verify_signature(str(archive), str(signature))
            assert success is False

    def test_apply_update_extraction_success(self, setup_dirs) -> None:
        install_dir, backup_dir, public_key_path = setup_dirs
        updater = OtaUpdater(str(install_dir), str(backup_dir), str(public_key_path))

        # Create a valid tar.gz file in memory
        archive_path = install_dir.parent / "update.tar.gz"
        tar_stream = io.BytesIO()
        with tarfile.open(fileobj=tar_stream, mode="w:gz") as tar:
            info = tarfile.TarInfo(name="app.py")
            content = b"print('version 2')"
            info.size = len(content)
            tar.addfile(tarinfo=info, fileobj=io.BytesIO(content))

        archive_path.write_bytes(tar_stream.getvalue())

        success = updater.apply_update(str(archive_path))
        assert success is True
        assert (install_dir / "app.py").read_text() == "print('version 2')"
        # Original backup should be preserved
        assert backup_dir.exists()
        assert (backup_dir / "app.py").read_text() == "print('version 1')"

    def test_apply_update_path_traversal_prevention(self, setup_dirs) -> None:
        install_dir, backup_dir, public_key_path = setup_dirs
        updater = OtaUpdater(str(install_dir), str(backup_dir), str(public_key_path))

        # Create a tar archive with a directory traversal filename
        archive_path = install_dir.parent / "update_traversal.tar.gz"
        tar_stream = io.BytesIO()
        with tarfile.open(fileobj=tar_stream, mode="w:gz") as tar:
            # Attempt directory traversal out of the install directory
            info = tarfile.TarInfo(name="../outside.py")
            content = b"malicious code"
            info.size = len(content)
            tar.addfile(tarinfo=info, fileobj=io.BytesIO(content))

        archive_path.write_bytes(tar_stream.getvalue())

        success = updater.apply_update(str(archive_path))
        # Extraction should fail and rollback
        assert success is False
        # Rollback should restore the original files
        assert (install_dir / "app.py").read_text() == "print('version 1')"

    def test_rollback(self, setup_dirs) -> None:
        install_dir, backup_dir, public_key_path = setup_dirs
        updater = OtaUpdater(str(install_dir), str(backup_dir), str(public_key_path))

        updater.backup_current()
        # Corrupt current install
        (install_dir / "app.py").write_text("print('corrupted')")

        success = updater.rollback()
        assert success is True
        assert (install_dir / "app.py").read_text() == "print('version 1')"
