"""
Unit tests for AssistantSkill short-term conversation history and long-term RAG memory queries.
"""

from unittest.mock import ANY, AsyncMock

import pytest

from packages.core.skills.assistant.skill import AssistantSkill
from packages.core.skills.base import SkillContext


@pytest.mark.unit
class TestAssistantMemory:
    @pytest.mark.asyncio
    async def test_short_term_history_preservation(self) -> None:
        skill = AssistantSkill()
        mock_llm = AsyncMock()
        mock_llm.generate = AsyncMock(return_value="My name is Puppy.")

        # Turn 1: Hello
        ctx1 = SkillContext(
            user_id="user_123",
            user_role="parent",
            user_name="Ramesh",
            language="en",
            raw_text="hello who are you?",
            slots={},
            ports={"llm": mock_llm},
        )
        res1 = await skill.execute(ctx1)
        assert res1.success is True
        assert res1.spoken_response == "My name is Puppy."
        mock_llm.generate.assert_called_once_with(
            "USER: hello who are you?", system=ANY
        )

        # Turn 2: What is your name?
        mock_llm.generate.reset_mock()
        mock_llm.generate.return_value = "As I said, I am Puppy."
        ctx2 = SkillContext(
            user_id="user_123",
            user_role="parent",
            user_name="Ramesh",
            language="en",
            raw_text="what is your name?",
            slots={},
            ports={"llm": mock_llm},
        )
        res2 = await skill.execute(ctx2)
        assert res2.success is True
        assert res2.spoken_response == "As I said, I am Puppy."

        # Check prompt contains the short term conversation history!
        called_prompt = mock_llm.generate.call_args[0][0]
        assert "USER: hello who are you?" in called_prompt
        assert "ASSISTANT: My name is Puppy." in called_prompt
        assert "USER: what is your name?" in called_prompt

    @pytest.mark.asyncio
    async def test_long_term_memory_rag_injection(self) -> None:
        skill = AssistantSkill()
        mock_llm = AsyncMock()
        mock_llm.generate = AsyncMock(return_value="Ramesh likes tea.")

        mock_memory = AsyncMock()
        # Mock a hit with high similarity
        mock_memory.search = AsyncMock(
            return_value=[
                {
                    "text": "Ramesh likes drinking black tea in the morning.",
                    "similarity": 0.8,
                }
            ]
        )

        ctx = SkillContext(
            user_id="user_123",
            user_role="parent",
            user_name="Ramesh",
            language="en",
            raw_text="what do I like to drink?",
            slots={},
            ports={"llm": mock_llm, "memory": mock_memory},
        )
        res = await skill.execute(ctx)
        assert res.success is True

        # Check memory search was queried
        mock_memory.search.assert_called_once_with("what do I like to drink?", k=3)

        # Check system prompt includes the retrieved long-term memory context!
        called_system = mock_llm.generate.call_args[1]["system"]
        assert "Ramesh likes drinking black tea" in called_system
