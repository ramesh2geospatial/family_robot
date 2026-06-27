"""Unit tests for packages.core.media.media_player."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from packages.core.media.media_player import MediaPlayer


class TestMediaPlayer:
    """Tests for MediaPlayer."""

    def test_init_checks_binaries(self) -> None:
        with patch("packages.core.media.media_player._get_mpv_path", return_value=None):
            mp = MediaPlayer()
            assert mp.can_play_inline is False

    def test_can_play_inline_true(self) -> None:
        with patch("packages.core.media.media_player._get_mpv_path", return_value="/usr/bin/mpv"), \
             patch("packages.core.media.media_player._ytdlp_available", return_value=True):
            mp = MediaPlayer()
            assert mp.can_play_inline is True

    def test_is_playing_no_process(self) -> None:
        mp = MediaPlayer()
        mp._process = None
        assert mp.is_playing() is False

    def test_is_playing_active_process(self) -> None:
        mp = MediaPlayer()
        mock_proc = MagicMock()
        mock_proc.poll.return_value = None  # still running
        mp._process = mock_proc
        assert mp.is_playing() is True

    def test_is_playing_terminated_process(self) -> None:
        mp = MediaPlayer()
        mock_proc = MagicMock()
        mock_proc.poll.return_value = 0  # exited
        mp._process = mock_proc
        assert mp.is_playing() is False

    @pytest.mark.asyncio
    async def test_play_browser_fallback(self) -> None:
        """When mpv is not available, play() should fall back to browser."""
        with patch("packages.core.media.media_player._get_mpv_path", return_value=None), \
             patch("packages.core.media.media_player._ytdlp_available", return_value=False), \
             patch("packages.core.media.media_player.webbrowser") as mock_wb:
            mp = MediaPlayer()
            title = await mp.play("Tum Hi Ho")
            assert "Tum Hi Ho" in title
            mock_wb.open.assert_called_once()
            url_arg = mock_wb.open.call_args[0][0]
            assert "youtube.com" in url_arg
            assert "Tum" in url_arg

    @pytest.mark.asyncio
    async def test_play_with_mpv(self) -> None:
        """When mpv + yt-dlp are available, play() should launch mpv."""
        with patch("packages.core.media.media_player._get_mpv_path", return_value="/usr/bin/mpv"), \
             patch("packages.core.media.media_player._ytdlp_available", return_value=True):
            mp = MediaPlayer()

            # Mock the resolve step
            mp._resolve_url_sync = MagicMock(
                return_value=("Tum Hi Ho - Arijit Singh", "https://example.com/audio.mp3")
            )

            with patch.object(mp, "_start_mpv") as mock_start:
                title = await mp.play("Tum Hi Ho")
                assert title == "Tum Hi Ho - Arijit Singh"
                mock_start.assert_called_once_with(
                    "https://example.com/audio.mp3",
                    "Tum Hi Ho - Arijit Singh",
                )

    @pytest.mark.asyncio
    async def test_play_resolve_fails_falls_back(self) -> None:
        """If yt-dlp fails, fall back to browser."""
        with patch("packages.core.media.media_player._get_mpv_path", return_value="/usr/bin/mpv"), \
             patch("packages.core.media.media_player._ytdlp_available", return_value=True), \
             patch("packages.core.media.media_player.webbrowser") as mock_wb:
            mp = MediaPlayer()
            mp._resolve_url_sync = MagicMock(return_value=("", ""))

            title = await mp.play("unknown song xyz")
            assert "browser" in title
            mock_wb.open.assert_called_once()

    @pytest.mark.asyncio
    async def test_stop_terminates_process(self) -> None:
        mp = MediaPlayer()
        mock_proc = MagicMock()
        mock_proc.poll.return_value = None
        mp._process = mock_proc
        mp._current_title = "Test Song"

        await mp.stop()

        mock_proc.terminate.assert_called_once()
        assert mp._process is None
        assert mp._current_title == ""

    @pytest.mark.asyncio
    async def test_pause_sends_ipc(self) -> None:
        mp = MediaPlayer()
        mock_proc = MagicMock()
        mock_proc.poll.return_value = None
        mp._process = mock_proc

        with patch.object(mp, "_send_ipc_command", return_value=True) as mock_ipc:
            result = await mp.pause()
            assert result is True
            mock_ipc.assert_called_once()

    @pytest.mark.asyncio
    async def test_play_empty_query_defaults(self) -> None:
        """Empty query defaults to trending Hindi songs."""
        with patch("packages.core.media.media_player._get_mpv_path", return_value=None), \
             patch("packages.core.media.media_player._ytdlp_available", return_value=False), \
             patch("packages.core.media.media_player.webbrowser") as mock_wb:
            mp = MediaPlayer()
            await mp.play("")
            url_arg = mock_wb.open.call_args[0][0]
            assert "trending" in url_arg
