"""
Centralized thread-safe database connection and transaction manager.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import sqlite3
import threading
from contextlib import contextmanager
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# ---------- sqlite-vec availability check ----------
_HAS_SQLITE_VEC = False
try:
    import sqlite_vec  # type: ignore[import-untyped]
    # Guard: Python on Windows standard builds often lacks extension loading
    if hasattr(sqlite3.Connection, "enable_load_extension"):
        _HAS_SQLITE_VEC = True
    else:
        logger.info(
            "sqlite3 lacks extension loading support; using brute-force fallback."
        )
except ImportError:
    logger.info("sqlite-vec not available; using brute-force fallback.")


class _InMemoryConnectionProxy:
    """Wraps a sqlite3 connection to make close() a no-op."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def __getattr__(self, name):
        return getattr(self._conn, name)

    def __enter__(self):
        return self._conn.__enter__()

    def __exit__(self, exc_type, exc_val, exc_tb):
        return self._conn.__exit__(exc_type, exc_val, exc_tb)

    def close(self) -> None:
        pass


class PersistenceContext:
    """Manages SQLite database connection lifecycles and schema setup.

    Supports thread-local active transaction connections and optional SQLCipher.
    """

    def __init__(self, db_path: str = "data/familyrobot.db") -> None:
        self.db_path = db_path
        self._db_ready = False
        self._lock = threading.Lock()
        self._local = threading.local()

    def _get_raw_connection(self) -> sqlite3.Connection:
        """Create a direct sqlite3 or sqlcipher connection."""
        if self.db_path == ":memory:":
            if not hasattr(self, "_memory_conn") or self._memory_conn is None:
                conn = sqlite3.connect(":memory:", check_same_thread=False)
                self._memory_conn = conn
            return _InMemoryConnectionProxy(self._memory_conn)  # type: ignore[return-value]

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
            # Inject key for SQLCipher encryption
            conn.execute(f"PRAGMA key = {json.dumps(key)};")

        conn.execute("PRAGMA journal_mode=WAL;")
        if _HAS_SQLITE_VEC:
            conn.enable_load_extension(True)
            sqlite_vec.load(conn)
        return conn

    def _ensure_db(self) -> None:
        """Setup table schemas if they do not exist."""
        if self._db_ready:
            return
        with self._lock:
            if self._db_ready:
                return
            Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
            conn = self._get_raw_connection()
            try:
                # 1. memories (RAG vector store)
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS memories (
                        id          TEXT PRIMARY KEY,
                        text        TEXT NOT NULL,
                        embedding   BLOB NOT NULL,
                        meta        TEXT,
                        created_at  TEXT NOT NULL
                    );
                    """
                )
                if _HAS_SQLITE_VEC:
                    conn.execute(
                        """
                        CREATE VIRTUAL TABLE IF NOT EXISTS memory_vec 
                        USING vec0(id TEXT PRIMARY KEY, embedding float[384])
                        """
                    )

                # 2. family_members (durable enrollment)
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS family_members (
                        user_id         TEXT PRIMARY KEY,
                        name            TEXT NOT NULL,
                        role            TEXT NOT NULL,
                        language        TEXT NOT NULL,
                        face_embedding  BLOB,
                        voice_embedding BLOB,
                        created_at      TEXT NOT NULL
                    );
                    """
                )

                # 3. conversation_history (chat logs with auto session timeout)
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS conversation_history (
                        id          INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id     TEXT NOT NULL,
                        role        TEXT NOT NULL,
                        content     TEXT NOT NULL,
                        timestamp   REAL NOT NULL
                    );
                    """
                )

                # 4. audit_logs (append-only database auditing)
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS audit_logs (
                        id          TEXT PRIMARY KEY,
                        ts          TEXT NOT NULL,
                        event       TEXT NOT NULL,
                        user_id     TEXT NOT NULL,
                        user_role   TEXT NOT NULL,
                        allowed     INTEGER,
                        details     TEXT
                    );
                    """
                )
                conn.commit()
            except Exception as exc:
                logger.error("Failed to initialize database schema: %s", exc)
                raise
            finally:
                conn.close()
            self._db_ready = True

    @contextmanager
    def get_connection(self):
        """Yields an active database connection context.

        Reuses the current thread's transaction connection if active.
        """
        self._ensure_db()
        if getattr(self._local, "conn", None) is not None:
            yield self._local.conn
            return

        conn = self._get_raw_connection()
        try:
            yield conn
        finally:
            conn.close()

    @contextmanager
    def transaction(self):
        """Yields a connection context wrapped in an SQLite transaction.

        Ensures all operations inside the scope succeed or fail together.
        Reuses thread-local connection if transaction is nested.
        """
        self._ensure_db()
        if getattr(self._local, "conn", None) is not None:
            yield self._local.conn
            return

        conn = self._get_raw_connection()
        self._local.conn = conn
        try:
            conn.execute("BEGIN TRANSACTION;")
            yield conn
            conn.commit()
        except Exception:
            try:
                conn.rollback()
            except Exception:
                pass
            raise
        finally:
            self._local.conn = None
            conn.close()
