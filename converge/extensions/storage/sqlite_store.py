"""
SQLite-backed Store implementation.

Uses the standard library sqlite3 module. Implements atomic put_if_absent
via INSERT OR IGNORE. Suitable for single-node or multi-process deployments
when all processes share the same database file.
"""
from __future__ import annotations

import pickle
import sqlite3
from pathlib import Path
from typing import Any

from converge.core.store import Store


class SQLiteStore(Store):
    """
    File-based Store using a single SQLite table (key TEXT PRIMARY KEY, value BLOB).

    Serialization uses pickle (same as FileStore) so Task, Pool, AgentDescriptor
    work without custom encoders. put_if_absent is atomic via INSERT OR IGNORE.
    """
    atomic_put_if_absent = True
    supports_locking = True

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self.path))
        self._conn.execute(
            "CREATE TABLE IF NOT EXISTS store (key TEXT PRIMARY KEY, value BLOB)",
        )
        self._conn.commit()

    def put(self, key: str, value: Any) -> None:
        data = pickle.dumps(value)
        self._conn.execute(
            "INSERT OR REPLACE INTO store (key, value) VALUES (?, ?)",
            (key, data),
        )
        self._conn.commit()

    def get(self, key: str) -> Any | None:
        row = self._conn.execute(
            "SELECT value FROM store WHERE key = ?",
            (key,),
        ).fetchone()
        if row is None:
            return None
        try:
            return pickle.loads(row[0])
        except Exception:
            return None

    def delete(self, key: str) -> None:
        self._conn.execute("DELETE FROM store WHERE key = ?", (key,))
        self._conn.commit()

    def list(self, prefix: str = "") -> list[str]:
        pattern = prefix + "%"
        rows = self._conn.execute(
            "SELECT key FROM store WHERE key LIKE ?",
            (pattern,),
        ).fetchall()
        return [r[0] for r in rows]

    def put_if_absent(self, key: str, value: Any) -> bool:
        data = pickle.dumps(value)
        cursor = self._conn.execute(
            "INSERT OR IGNORE INTO store (key, value) VALUES (?, ?)",
            (key, data),
        )
        self._conn.commit()
        return cursor.rowcount == 1
