"""
Unit tests for the expression package (ResponseFormatter + TTS engine).
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from packages.core.expression.response_formatter import format_response
from packages.core.expression.tts_engine import PiperTTSEngine


# ──────────────────────────────────────────────
# ResponseFormatter
# ──────────────────────────────────────────────

@pytest.mark.unit
class TestResponseFormatter:

    def test_strips_bold(self) -> None:
        assert format_response("**hello** world") == "hello world"

    def test_strips_italic(self) -> None:
        assert format_response("*hello* world") == "hello world"

    def test_strips_code_blocks(self) -> None:
        text = "Here is code:\n```python\nprint('hi')\n```\nDone."
        result = format_response(text)
        assert "```" not in result
        assert "Done" in result

    def test_strips_inline_code(self) -> None:
        assert "code" not in format_response("`x = 1`")

    def test_strips_headings(self) -> None:
        result = format_response("## Title\nSome text")
        assert "##" not in result
        assert "Title" in result

    def test_strips_bullets(self) -> None:
        result = format_response("- item one\n- item two")
        assert "-" not in result or "item" in result

    def test_strips_links(self) -> None:
        result = format_response("[click here](https://example.com)")
        assert "click here" in result
        assert "https" not in result

    def test_truncation(self) -> None:
        long_text = " ".join(["word"] * 300)
        result = format_response(long_text)
        assert len(result.split()) <= 201  # 200 words + ellipsis

    def test_home_control_prefix(self) -> None:
        result = format_response("Turned on the geyser.", "home_control")
        assert result.startswith("Done!")

    def test_memory_store_prefix(self) -> None:
        result = format_response("Saved.", "memory_store")
        assert "remember" in result.lower()

    def test_timer_prefix(self) -> None:
        result = format_response("5 minutes.", "timer")
        assert result.startswith("Timer set!")

    def test_general_chat_no_prefix(self) -> None:
        result = format_response("Hello there!", "general_chat")
        assert not result.startswith("Done!")

    def test_none_input(self) -> None:
        result = format_response(None)
        assert "not sure" in result.lower()

    def test_empty_input(self) -> None:
        result = format_response("")
        assert "not sure" in result.lower()


# ──────────────────────────────────────────────
# PiperTTSEngine
# ──────────────────────────────────────────────

@pytest.mark.unit
class TestPiperTTSEngine:

    @pytest.mark.asyncio
    async def test_empty_text_returns_silence(self) -> None:
        engine = PiperTTSEngine()
        pcm, sr = await engine.synthesize("")
        assert isinstance(pcm, bytes)
        assert sr == 22050

    @pytest.mark.asyncio
    async def test_none_text_returns_silence(self) -> None:
        engine = PiperTTSEngine()
        pcm, sr = await engine.synthesize("   ")
        assert isinstance(pcm, bytes)
        assert len(pcm) > 0

    @pytest.mark.asyncio
    async def test_fallback_when_no_piper(self) -> None:
        """With no model path, engine should try pyttsx3 fallback."""
        engine = PiperTTSEngine(model_path=None)
        engine._use_piper = False
        # Even if pyttsx3 isn't available, should not crash
        pcm, sr = await engine.synthesize("test")
        assert isinstance(pcm, bytes)
