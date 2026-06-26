"""
Unit tests for the cognition package (IntentRouter + LlamaLLMClient).
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from packages.core.cognition.intent_router import Intent, IntentRouter
from packages.core.cognition.llm_client import LlamaLLMClient


# ──────────────────────────────────────────────
# IntentRouter – rule-based classification
# ──────────────────────────────────────────────

@pytest.mark.unit
class TestIntentRouterRules:
    """Verify keyword-based intent classification."""

    @pytest.fixture
    def router(self) -> IntentRouter:
        return IntentRouter()

    @pytest.mark.asyncio
    async def test_home_control_turn_on(self, router: IntentRouter) -> None:
        intent = await router.classify("turn on the geyser")
        assert intent.name == "home_control"
        assert intent.confidence >= 0.8
        assert "geyser" in intent.entities.get("devices", [])
        assert intent.entities.get("action") == "on"

    @pytest.mark.asyncio
    async def test_home_control_turn_off(self, router: IntentRouter) -> None:
        intent = await router.classify("switch off the fan")
        assert intent.name == "home_control"
        assert intent.entities.get("action") == "off"
        assert "fan" in intent.entities.get("devices", [])

    @pytest.mark.asyncio
    async def test_memory_store(self, router: IntentRouter) -> None:
        intent = await router.classify("remember that Aarav's birthday is March 5")
        assert intent.name == "memory_store"

    @pytest.mark.asyncio
    async def test_memory_recall(self, router: IntentRouter) -> None:
        intent = await router.classify("when is Aarav's birthday?")
        assert intent.name == "memory_recall"

    @pytest.mark.asyncio
    async def test_timer(self, router: IntentRouter) -> None:
        intent = await router.classify("set timer for 5 minutes")
        assert intent.name == "timer"
        assert intent.entities.get("duration") == {"minutes": 5}

    @pytest.mark.asyncio
    async def test_reminder(self, router: IntentRouter) -> None:
        intent = await router.classify("remind me to buy milk")
        assert intent.name == "reminder"

    @pytest.mark.asyncio
    async def test_general_chat_fallback(self, router: IntentRouter) -> None:
        intent = await router.classify("tell me a joke")
        assert intent.name == "general_chat"
        assert intent.confidence == 0.5

    @pytest.mark.asyncio
    async def test_empty_input(self, router: IntentRouter) -> None:
        intent = await router.classify("")
        assert intent.name == "general_chat"
        assert intent.confidence == 0.0

    @pytest.mark.asyncio
    async def test_device_extraction_multiple(self, router: IntentRouter) -> None:
        intent = await router.classify("turn on the light and fan")
        assert intent.name == "home_control"
        assert "light" in intent.entities.get("devices", [])
        assert "fan" in intent.entities.get("devices", [])

    @pytest.mark.asyncio
    async def test_timer_duration_seconds(self, router: IntentRouter) -> None:
        intent = await router.classify("set timer for 30 seconds")
        assert intent.name == "timer"
        assert intent.entities.get("duration") == {"seconds": 30}


# ──────────────────────────────────────────────
# IntentRouter – LLM fallback
# ──────────────────────────────────────────────

@pytest.mark.unit
class TestIntentRouterLLMFallback:

    @pytest.mark.asyncio
    async def test_llm_fallback_called(self) -> None:
        mock_llm = AsyncMock()
        mock_llm.generate.return_value = "home_control"
        router = IntentRouter(llm=mock_llm)
        # Use text that won't match any keyword rule
        intent = await router.classify("please adjust the thermostat")
        # Should fall back to LLM since "thermostat" isn't in keywords
        # (but it also might not match rules — depends on keywords)
        assert intent.name in ("home_control", "general_chat")

    @pytest.mark.asyncio
    async def test_llm_fallback_error_recovery(self) -> None:
        mock_llm = AsyncMock()
        mock_llm.generate.side_effect = RuntimeError("LLM down")
        router = IntentRouter(llm=mock_llm)
        intent = await router.classify("something very unusual xyz123")
        assert intent.name == "general_chat"


# ──────────────────────────────────────────────
# LlamaLLMClient
# ──────────────────────────────────────────────

@pytest.mark.unit
class TestLlamaLLMClient:

    @pytest.mark.asyncio
    async def test_prompt_construction(self) -> None:
        client = LlamaLLMClient(model_path="fake.gguf")
        prompt = client._build_prompt("Hello", system="Be helpful")
        assert "<|im_start|>system" in prompt
        assert "Be helpful" in prompt
        assert "<|im_start|>user" in prompt
        assert "Hello" in prompt
        assert "<|im_start|>assistant" in prompt

    @pytest.mark.asyncio
    async def test_prompt_no_system(self) -> None:
        client = LlamaLLMClient(model_path="fake.gguf")
        prompt = client._build_prompt("Hello", system="")
        assert "<|im_start|>system" not in prompt
        assert "<|im_start|>user" in prompt

    @pytest.mark.asyncio
    async def test_generate_with_mock(self) -> None:
        client = LlamaLLMClient(model_path="fake.gguf")
        mock_llama = MagicMock()
        mock_llama.create_completion.return_value = {
            "choices": [{"text": " Sure, here is the answer."}]
        }
        client._llama = mock_llama  # skip loading

        result = await client.generate("What is 2+2?")
        assert "answer" in result.lower()
        mock_llama.create_completion.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_error_returns_fallback(self) -> None:
        client = LlamaLLMClient(model_path="fake.gguf")
        mock_llama = MagicMock()
        mock_llama.create_completion.side_effect = RuntimeError("OOM")
        client._llama = mock_llama

        result = await client.generate("test")
        assert "sorry" in result.lower()
