"""
Persistent vector-searchable memory store.

Uses SQLite WAL for crash-safety and sentence-transformers for embeddings.
Attempts sqlite-vec for fast KNN; falls back to brute-force cosine
similarity (viable for family-scale < 10 K entries).
"""

from __future__ import annotations

import asyncio
import json
import logging
import sqlite3
import struct
import uuid
from datetime import datetime, timezone
from math import sqrt
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# ---------- sqlite-vec availability check ----------
_HAS_SQLITE_VEC = False
try:
    import sqlite_vec  # type: ignore[import-untyped]

    _HAS_SQLITE_VEC = True
except ImportError:
    logger.info("sqlite-vec not available; using brute-force cosine fallback.")


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    """Compute cosine similarity between two equal-length vectors."""
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = sqrt(sum(x * x for x in a))
    norm_b = sqrt(sum(x * x for x in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def _embed_to_blob(embedding: list[float]) -> bytes:
    """Pack a float list into a compact binary blob (little-endian float32)."""
    return struct.pack(f"<{len(embedding)}f", *embedding)


def _blob_to_embed(blob: bytes) -> list[float]:
    """Unpack a binary blob back to a float list."""
    count = len(blob) // 4
    return list(struct.unpack(f"<{count}f", blob))


class MemoryStore:
    """SQLite WAL + vector search memory store.

    Satisfies the ``MemoryPort`` protocol.
    """

    _CREATE_TABLE = """
    CREATE TABLE IF NOT EXISTS memories (
        id          TEXT PRIMARY KEY,
        text        TEXT NOT NULL,
        embedding   BLOB NOT NULL,
        meta        TEXT,
        created_at  TEXT NOT NULL
    );
    """

    def __init__(
        self,
        db_path: str = "memory.db",
        embedding_model: str = "all-MiniLM-L6-v2",
    ) -> None:
        self.db_path = db_path
        self._embedding_model_name = embedding_model
        self._embedder: Optional[object] = None
        self._db_ready = False

    # ---- lazy init helpers ----

    def _get_connection(self) -> sqlite3.Connection:
        import os

        key = os.getenv("DB_ENCRYPTION_KEY")
        sqlite_lib = sqlite3

        if key:
            try:
                from sqlcipher3 import dbapi2 as sqlite_lib
            except ImportError:
                try:
                    from pysqlcipher3 import dbapi2 as sqlite_lib
                except ImportError:
                    pass

        conn = sqlite_lib.connect(self.db_path)
        if key:
            conn.execute(f"PRAGMA key = {json.dumps(key)};")

        conn.execute("PRAGMA journal_mode=WAL;")
        if _HAS_SQLITE_VEC:
            conn.enable_load_extension(True)
            sqlite_vec.load(conn)
        return conn

    def _ensure_db(self) -> None:
        if self._db_ready:
            return
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        conn = self._get_connection()
        try:
            conn.execute(self._CREATE_TABLE)
            if _HAS_SQLITE_VEC:
                # Create virtual table for fast KNN search
                conn.execute(
                    "CREATE VIRTUAL TABLE IF NOT EXISTS memory_vec "
                    "USING vec0(id TEXT PRIMARY KEY, embedding float[384])"
                )
            conn.commit()
        finally:
            conn.close()
        self._db_ready = True

    def _ensure_embedder(self) -> None:
        if self._embedder is not None:
            return
        from sentence_transformers import (
            SentenceTransformer,  # type: ignore[import-untyped]
        )

        logger.info("Loading embedding model: %s", self._embedding_model_name)
        self._embedder = SentenceTransformer(self._embedding_model_name)
        logger.info("Embedding model loaded.")

    def _embed(self, text: str) -> list[float]:
        self._ensure_embedder()
        vec = self._embedder.encode(text, convert_to_numpy=True)  # type: ignore[union-attr]
        return vec.tolist()

    # ---- public API (MemoryPort) ----

    async def store(self, text: str, *, meta: dict | None = None) -> str:
        """Embed *text* and persist it. Returns a UUID string."""

        def _do_store() -> str:
            self._ensure_db()
            embedding = self._embed(text)
            mem_id = str(uuid.uuid4())
            now = datetime.now(timezone.utc).isoformat()
            meta_json = json.dumps(meta) if meta else None
            blob = _embed_to_blob(embedding)

            conn = self._get_connection()
            try:
                conn.execute(
                    "INSERT INTO memories "
                    "(id, text, embedding, meta, created_at) "
                    "VALUES (?, ?, ?, ?, ?)",
                    (mem_id, text, blob, meta_json, now),
                )
                if _HAS_SQLITE_VEC:
                    conn.execute(
                        "INSERT INTO memory_vec (id, embedding) " "VALUES (?, ?)",
                        (mem_id, blob),
                    )
                conn.commit()
            finally:
                conn.close()
            logger.info("Stored memory %s (%d chars)", mem_id[:8], len(text))
            return mem_id

        return await asyncio.to_thread(_do_store)

    async def search(self, query: str, *, k: int = 5) -> list[dict]:
        """Return the *k* most similar memories to *query*."""

        def _do_search() -> list[dict]:
            self._ensure_db()
            query_vec = self._embed(query)
            query_blob = _embed_to_blob(query_vec)

            conn = self._get_connection()
            try:
                if _HAS_SQLITE_VEC:
                    return self._search_vec(conn, query_blob, k)
                return self._search_brute(conn, query_vec, k)
            finally:
                conn.close()

        return await asyncio.to_thread(_do_search)

    def _search_vec(
        self,
        conn: sqlite3.Connection,
        query_blob: bytes,
        k: int,
    ) -> list[dict]:
        """KNN search via sqlite-vec virtual table."""
        rows = conn.execute(
            "SELECT v.id, v.distance, m.text, m.meta, m.created_at "
            "FROM memory_vec v "
            "JOIN memories m ON v.id = m.id "
            "WHERE v.embedding MATCH ? "
            "ORDER BY v.distance "
            "LIMIT ?",
            (query_blob, k),
        ).fetchall()
        results: list[dict] = []
        for row_id, dist, text, meta_json, ts in rows:
            # sqlite-vec returns L2 distance; convert to ~cosine
            score = max(0.0, 1.0 - dist)
            results.append(
                {
                    "id": row_id,
                    "text": text,
                    "meta": (json.loads(meta_json) if meta_json else None),
                    "score": round(score, 4),
                    "created_at": ts,
                }
            )
        return results

    def _search_brute(
        self,
        conn: sqlite3.Connection,
        query_vec: list[float],
        k: int,
    ) -> list[dict]:
        """Brute-force cosine similarity fallback."""
        rows = conn.execute(
            "SELECT id, text, embedding, meta, created_at " "FROM memories"
        ).fetchall()

        scored: list[tuple[float, dict]] = []
        for row_id, text, blob, meta_json, ts in rows:
            row_vec = _blob_to_embed(blob)
            score = _cosine_similarity(query_vec, row_vec)
            scored.append(
                (
                    score,
                    {
                        "id": row_id,
                        "text": text,
                        "meta": (json.loads(meta_json) if meta_json else None),
                        "score": round(score, 4),
                        "created_at": ts,
                    },
                )
            )
        scored.sort(key=lambda x: x[0], reverse=True)
        return [item for _, item in scored[:k]]

    async def delete(self, memory_id: str) -> bool:
        """Delete a memory by *memory_id*. Returns True if a row was deleted."""

        def _do_delete() -> bool:
            self._ensure_db()
            conn = self._get_connection()
            try:
                cursor = conn.execute(
                    "DELETE FROM memories WHERE id = ?", (memory_id,)
                )
                if _HAS_SQLITE_VEC:
                    conn.execute(
                        "DELETE FROM memory_vec WHERE id = ?", (memory_id,)
                    )
                conn.commit()
                deleted = cursor.rowcount > 0
            finally:
                conn.close()
            if deleted:
                logger.info("Deleted memory %s", memory_id[:8])
            return deleted

        return await asyncio.to_thread(_do_delete)
