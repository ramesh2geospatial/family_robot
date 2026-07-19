"""
Unit tests for the PWA webapp status helper and endpoints.
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from packages.core.webapp.app import app, set_state
from packages.core.webapp.status_helper import read_robot_status, update_robot_status


@pytest.mark.unit
class TestWebappStatus:

    @pytest.fixture(autouse=True)
    def clean_files(self):
        # Reset and clean status files before/after tests
        status_file = Path("data/robot_status.json")
        cmd_file = Path("data/media_command.json")
        
        for f in (status_file, cmd_file):
            if f.exists():
                try:
                    f.unlink()
                except Exception:
                    pass
        yield
        for f in (status_file, cmd_file):
            if f.exists():
                try:
                    f.unlink()
                except Exception:
                    pass

    def test_status_helper_write_read(self) -> None:
        # Write status
        update_robot_status(
            status="listening",
            current_song="Song A",
            is_playing_music=True,
            last_speech_heard="play music",
            last_speech_spoken="Playing Song A"
        )
        
        # Read back
        data = read_robot_status()
        assert data["status"] == "listening"
        assert data["current_song"] == "Song A"
        assert data["is_playing_music"] is True
        assert data["last_speech_heard"] == "play music"
        assert data["last_speech_spoken"] == "Playing Song A"

    def test_status_endpoint_loads_helper(self) -> None:
        # Prepare state mocks
        mock_identity = MagicMock()
        mock_identity.list_members.return_value = []
        set_state(identity_store=mock_identity)
        
        update_robot_status(
            status="speaking",
            current_song="Song B",
            is_playing_music=True,
            last_speech_heard="who is Ramesh",
            last_speech_spoken="Ramesh is the parent"
        )

        client = TestClient(app)
        response = client.get("/api/status")
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "speaking"
        assert data["current_song"] == "Song B"
        assert data["is_playing_music"] is True
        assert data["last_speech_heard"] == "who is Ramesh"
        assert data["last_speech_spoken"] == "Ramesh is the parent"

    def test_media_command_queues_command(self) -> None:
        client = TestClient(app)
        response = client.post(
            "/api/media/command",
            json={"action": "play", "query": "Tum Hi Ho"}
        )
        assert response.status_code == 200
        
        # Verify file exists and has correct payload
        cmd_file = Path("data/media_command.json")
        assert cmd_file.exists()
        
        content = json.loads(cmd_file.read_text(encoding="utf-8"))
        assert content["action"] == "play"
        assert content["query"] == "Tum Hi Ho"
        assert "ts" in content
