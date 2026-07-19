"""
Comprehensive unit tests for the new intelligence upgrades:
ContextBuilder, ToolRegistry, ToolExecutor, IntentPrompts, ProactiveEngine, Personality,
and structured IntentRouter LLM classification.
"""

import json
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from packages.core.cognition.context_builder import ContextBuilder
from packages.core.cognition.intent_prompts import INTENT_CLASSIFICATION_SYSTEM
from packages.core.cognition.intent_router import Intent, IntentRouter
from packages.core.cognition.proactive_engine import ProactiveEngine
from packages.core.cognition.tool_executor import ToolExecutor
from packages.core.cognition.tool_registry import ToolDefinition, ToolRegistry, build_default_tools
from packages.core.expression.personality import get_personality_block


# ── 1. ContextBuilder Tests ──
@pytest.mark.asyncio
async def test_context_builder_system_prompt_all_features() -> None:
    builder = ContextBuilder()
    mock_memory = AsyncMock()
    mock_memory.search.return_value = [{"text": "Ramesh likes black coffee", "score": 0.9}]

    active_state = {"is_playing_music": True, "current_song": "Tum Hi Ho"}

    system_prompt = await builder.build_system_prompt(
        user_name="Ramesh",
        user_role="parent",
        language="hi",
        memory_port=mock_memory,
        query="what do I like?",
        is_guest=False,
        active_state=active_state,
    )

    assert "Ramesh" in system_prompt
    assert "parent" in system_prompt
    # Hindi instruction check
    assert "Devanagari" in system_prompt
    # RAG check
    assert "Ramesh likes black coffee" in system_prompt
    # Active state check
    assert "Tum Hi Ho" in system_prompt


@pytest.mark.asyncio
async def test_context_builder_system_prompt_guest_no_rag() -> None:
    builder = ContextBuilder()
    mock_memory = AsyncMock()

    system_prompt = await builder.build_system_prompt(
        user_name="GuestUser",
        user_role="guest",
        language="en",
        memory_port=mock_memory,
        query="tell me a secret",
        is_guest=True,
    )

    # RAG should not search
    mock_memory.search.assert_not_called()
    assert "GuestUser" in system_prompt


def test_context_builder_history_prompt() -> None:
    builder = ContextBuilder(max_history_chars=100)

    class MockTurn:
        def __init__(self, role: str, content: str):
            self.role = role
            self.content = content

    history = [
        MockTurn("user", "Hello robot"),
        MockTurn("assistant", "Hello Ramesh"),
        MockTurn("user", "How are you?"),
    ]

    prompt = builder.build_history_prompt(history, "I am fine")
    assert "USER: How are you?" in prompt
    assert "USER: I am fine" in prompt


# ── 2. ToolRegistry Tests ──
def test_tool_registry_registration() -> None:
    registry = ToolRegistry()

    async def dummy_handler() -> str:
        return "done"

    tool = ToolDefinition(
        name="test_tool",
        description="A dummy test tool",
        parameters={"properties": {}},
        handler=dummy_handler,
    )

    registry.register(tool)
    assert registry.get("test_tool") == tool
    assert len(registry.list_tools()) == 1

    prompt_block = registry.get_tool_prompt_block()
    assert "test_tool" in prompt_block


def test_build_default_tools() -> None:
    mock_home = MagicMock()
    mock_media = MagicMock()
    mock_memory = MagicMock()

    ports = {
        "home": mock_home,
        "media_player": mock_media,
        "memory": mock_memory,
    }

    registry = build_default_tools(ports)
    tools = registry.list_tools()
    tool_names = [t.name for t in tools]

    assert "control_device" in tool_names
    assert "play_song" in tool_names
    assert "store_memory" in tool_names
    assert "search_memory" in tool_names
    assert "get_time" in tool_names


# ── 3. ToolExecutor Tests ──
@pytest.mark.asyncio
async def test_tool_executor_is_tool_call() -> None:
    registry = ToolRegistry()
    executor = ToolExecutor(registry)

    assert executor.is_tool_call('{"tool": "get_time", "args": {}}') is True
    assert executor.is_tool_call("Just normal chat response") is False


@pytest.mark.asyncio
async def test_tool_executor_execute_success() -> None:
    registry = ToolRegistry()

    async def dummy_handler(target: str) -> str:
        return f"Dummy target is {target}"

    tool = ToolDefinition(
        name="dummy",
        description="Dummy desc",
        parameters={"properties": {"target": {"type": "string"}}},
        handler=dummy_handler,
    )
    registry.register(tool)

    executor = ToolExecutor(registry)
    res = await executor.execute('{"tool": "dummy", "args": {"target": "world"}}')
    assert res == "Dummy target is world"


@pytest.mark.asyncio
async def test_tool_executor_execute_unknown_tool() -> None:
    registry = ToolRegistry()
    executor = ToolExecutor(registry)
    res = await executor.execute('{"tool": "unknown_tool", "args": {}}')
    assert "unknown_tool" in res


@pytest.mark.asyncio
async def test_tool_executor_execute_malformed_json() -> None:
    registry = ToolRegistry()
    executor = ToolExecutor(registry)
    res = await executor.execute('{"tool": "get_time", malformed JSON')
    assert "confused" in res


# ── 4. IntentPrompts Tests ──
def test_intent_prompts_system_prompt() -> None:
    assert len(INTENT_CLASSIFICATION_SYSTEM) > 0
    assert "home_control" in INTENT_CLASSIFICATION_SYSTEM
    assert "control_geyser" in INTENT_CLASSIFICATION_SYSTEM
    assert "general_chat" in INTENT_CLASSIFICATION_SYSTEM


# ── 5. ProactiveEngine Tests ──
@pytest.mark.asyncio
async def test_proactive_engine_quiet_hours() -> None:
    engine = ProactiveEngine(quiet_start=22, quiet_end=6)
    # Mock datetime to 11 PM
    with patch("packages.core.cognition.proactive_engine.datetime") as mock_dt:
        mock_dt.now.return_value = datetime(2026, 7, 19, 23, 0, 0)
        res = await engine.check()
        assert res is None


@pytest.mark.asyncio
async def test_proactive_engine_morning_greeting() -> None:
    engine = ProactiveEngine()
    mock_memory = AsyncMock()
    mock_memory.search.return_value = []

    # Mock datetime to 8 AM
    with patch("packages.core.cognition.proactive_engine.datetime") as mock_dt:
        mock_dt.now.return_value = datetime(2026, 7, 19, 8, 0, 0)
        res = await engine.check(memory_port=mock_memory, current_user="Ramesh")
        assert "Good morning, Ramesh!" in res

        # Second call same day same user should return None (already greeted)
        res2 = await engine.check(memory_port=mock_memory, current_user="Ramesh")
        assert res2 is None


@pytest.mark.asyncio
async def test_proactive_engine_geyser_state_warning() -> None:
    engine = ProactiveEngine()
    mock_home = AsyncMock()
    mock_home.get_state.return_value = {"on": True}

    # Mock datetime to 4 PM (not morning, not quiet hours)
    with patch("packages.core.cognition.proactive_engine.datetime") as mock_dt:
        mock_dt.now.return_value = datetime(2026, 7, 19, 16, 0, 0)
        res = await engine.check(home_port=mock_home, current_user="Ramesh")
        assert "geyser" in res


# ── 6. Personality Tests ──
def test_personality_block_roles() -> None:
    child_block = get_personality_block(user_role="child", user_name="Arjun")
    elder_block = get_personality_block(user_role="elder", user_name="Dadaji")
    unknown_block = get_personality_block(user_role="unknown")

    assert "encouraging" in child_block or "beta" in child_block
    assert "ji" in elder_block
    # should fall back to adult profile
    assert "adult" in unknown_block or "conversational" in unknown_block


# ── 7. IntentRouter LLM Fallback Tests ──
@pytest.mark.asyncio
async def test_intent_router_llm_classify_valid_json() -> None:
    mock_llm = AsyncMock()
    mock_llm.generate.return_value = '{"intent": "play_music", "entities": {"song": "Tum Hi Ho"}}'

    router = IntentRouter(llm=mock_llm)
    # Query must NOT match any keyword rule (so it bypasses keywords to LLM)
    intent = await router.classify("some query that triggers no keyword rules")

    assert intent.name == "play_music"
    assert intent.entities == {"song": "Tum Hi Ho"}
    assert intent.confidence == 0.75


@pytest.mark.asyncio
async def test_intent_router_llm_classify_malformed_json_fallback() -> None:
    mock_llm = AsyncMock()
    mock_llm.generate.return_value = "This is not a JSON object"

    router = IntentRouter(llm=mock_llm)
    # Query must NOT match any keyword rule
    intent = await router.classify("some query that triggers no keyword rules")

    assert intent.name == "general_chat"
    assert intent.confidence == 0.4
