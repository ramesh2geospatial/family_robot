"""
Unit tests for the memory store.
"""

from __future__ import annotations

import asyncio
import json
import struct
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from packages.core.memory.memory_store import MemoryStore, _cosine_similarity


# ──────────────────────────────────────────────
# Helper: deterministic mock embedder
# ──────────────────────────────────────────────

def _make_mock_embedder():
    """Return a mock SentenceTransformer that produces deterministic 4-d vectors."""
    embedder = MagicMock()
    _call_count = {"n": 0}

    def _encode(text: str, convert_to_numpy: bool = True):
        _call_count["n"] += 1
        # Simple hash-based deterministic embedding
        h = hash(text) % 10000
        vec = np.array([h / 10000, (h % 100) / 100, (h % 10) / 10, 0.5], dtype=np.float32)
        # Normalise
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = vec / norm
        return vec

    embedder.encode = _encode
    return embedder


# ──────────────────────────────────────────────
# Tests
# ──────────────────────────────────────────────

@pytest.mark.unit
class TestCosine:

    def test_identical_vectors(self) -> None:
        assert _cosine_similarity([1, 0, 0], [1, 0, 0]) == pytest.approx(1.0)

    def test_orthogonal_vectors(self) -> None:
        assert _cosine_similarity([1, 0], [0, 1]) == pytest.approx(0.0)

    def test_zero_vector(self) -> None:
        assert _cosine_similarity([0, 0], [1, 1]) == pytest.approx(0.0)


@pytest.mark.unit
class TestMemoryStore:

    @pytest.fixture
    def store(self, tmp_path: Path) -> MemoryStore:
        db = str(tmp_path / "test_memory.db")
        ms = MemoryStore(db_path=db, embedding_model="mock")
        # Inject mock embedder
        ms._embedder = _make_mock_embedder()
        return ms

    @pytest.mark.asyncio
    async def test_store_returns_uuid(self, store: MemoryStore) -> None:
        mid = await store.store("Aarav's birthday is March 5")
        assert isinstance(mid, str)
        assert len(mid) == 36  # UUID format

    @pytest.mark.asyncio
    async def test_store_and_search(self, store: MemoryStore) -> None:
        await store.store("Aarav's birthday is March 5")
        await store.store("The WiFi password is foobar123")
        results = await store.search("birthday", k=2)
        assert len(results) == 2
        assert all("text" in r for r in results)
        assert all("score" in r for r in results)

    @pytest.mark.asyncio
    async def test_search_returns_ordered_by_score(self, store: MemoryStore) -> None:
        await store.store("alpha")
        await store.store("beta")
        await store.store("gamma")
        results = await store.search("alpha", k=3)
        scores = [r["score"] for r in results]
        assert scores == sorted(scores, reverse=True)

    @pytest.mark.asyncio
    async def test_delete(self, store: MemoryStore) -> None:
        mid = await store.store("temporary note")
        deleted = await store.delete(mid)
        assert deleted is True
        # Second delete should return False
        deleted2 = await store.delete(mid)
        assert deleted2 is False

    @pytest.mark.asyncio
    async def test_search_empty_db(self, store: MemoryStore) -> None:
        results = await store.search("anything", k=5)
        assert results == []

    @pytest.mark.asyncio
    async def test_store_with_metadata(self, store: MemoryStore) -> None:
        mid = await store.store("test", meta={"source": "voice", "user": "aarav"})
        results = await store.search("test", k=1)
        assert results[0]["meta"]["source"] == "voice"

    @pytest.mark.asyncio
    async def test_schema_auto_created(self, tmp_path: Path) -> None:
        db = str(tmp_path / "fresh.db")
        ms = MemoryStore(db_path=db)
        ms._embedder = _make_mock_embedder()
        mid = await ms.store("first entry ever")
        assert isinstance(mid, str)
