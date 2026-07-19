"""
Unit tests for the Auto-Memory Extraction utility.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
import pytest

from packages.core.governance.identity import FamilyMember, Role
from packages.core.cognition.memory_extractor import extract_and_store_memories


@pytest.mark.unit
class TestMemoryExtractor:

    @pytest.mark.asyncio
    async def test_extract_and_store_success(self) -> None:
        mock_llm = AsyncMock()
        mock_llm.generate.return_value = "Arjun starts school at 8 AM\nRamesh loves ginger tea"

        mock_store = AsyncMock()
        # No similar memories found
        mock_store.search.return_value = []
        mock_store.store = AsyncMock()

        user = FamilyMember(user_id="parent_default", name="Ramesh", role=Role.PARENT)

        await extract_and_store_memories(
            llm=mock_llm,
            memory_store=mock_store,
            user=user,
            user_text="Arjun goes to school at 8 and I love ginger tea",
            robot_response="Okay, I will keep that in mind."
        )

        assert mock_store.store.call_count == 2
        mock_store.store.assert_any_call("Arjun starts school at 8 AM", meta={"extracted": True, "source": "local_llm_auto"})
        mock_store.store.assert_any_call("Ramesh loves ginger tea", meta={"extracted": True, "source": "local_llm_auto"})

    @pytest.mark.asyncio
    async def test_extract_and_store_duplicate(self) -> None:
        mock_llm = AsyncMock()
        mock_llm.generate.return_value = "Arjun starts school at 8 AM"

        mock_store = AsyncMock()
        # Similar memory exists with score 0.92
        mock_store.search.return_value = [{"text": "Arjun school starts at 8 AM", "score": 0.92}]
        mock_store.store = AsyncMock()

        user = FamilyMember(user_id="parent_default", name="Ramesh", role=Role.PARENT)

        await extract_and_store_memories(
            llm=mock_llm,
            memory_store=mock_store,
            user=user,
            user_text="Arjun has school at 8",
            robot_response="Noted."
        )

        mock_store.store.assert_not_called()

    @pytest.mark.asyncio
    async def test_extract_and_store_guest(self) -> None:
        mock_llm = AsyncMock()
        mock_store = AsyncMock()
        # Guest user
        user = FamilyMember(user_id="guest_default", name="GuestUser", role=Role.GUEST)

        await extract_and_store_memories(
            llm=mock_llm,
            memory_store=mock_store,
            user=user,
            user_text="I love biryani",
            robot_response="Yum."
        )

        mock_llm.generate.assert_not_called()
        mock_store.store.assert_not_called()

    @pytest.mark.asyncio
    async def test_extract_and_store_none(self) -> None:
        mock_llm = AsyncMock()
        mock_llm.generate.return_value = "NONE"

        mock_store = AsyncMock()
        mock_store.store = AsyncMock()

        user = FamilyMember(user_id="parent_default", name="Ramesh", role=Role.PARENT)

        await extract_and_store_memories(
            llm=mock_llm,
            memory_store=mock_store,
            user=user,
            user_text="hello how are you",
            robot_response="I'm good, thank you!"
        )

        mock_store.store.assert_not_called()
