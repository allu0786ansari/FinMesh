"""A node's memory of the request nonces it has answered, kept across restarts (X7).

:class:`RequestGuard` refuses a request whose nonce it has seen. In process, that memory
is a set; a restarted node process would forget it, so a request answered just before the
restart could be replayed within its validity window. :class:`PersistentNonces` is a
drop-in replacement for that set (``in`` and ``add``), backed by SQLite, so the guard
itself, bank-side code, stays unchanged.
"""

from __future__ import annotations

import sqlite3
import threading
from pathlib import Path


class PersistentNonces:
    def __init__(self, path: Path | str) -> None:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(path), check_same_thread=False, timeout=30)
        self._lock = threading.Lock()
        with self._lock, self._conn:
            self._conn.execute("PRAGMA journal_mode=WAL")
            self._conn.execute("CREATE TABLE IF NOT EXISTS seen (nonce BLOB PRIMARY KEY)")

    def __contains__(self, nonce: object) -> bool:
        if not isinstance(nonce, bytes):
            return False
        with self._lock:
            row = self._conn.execute("SELECT 1 FROM seen WHERE nonce = ?", (nonce,)).fetchone()
        return row is not None

    def add(self, nonce: bytes) -> None:
        with self._lock, self._conn:
            self._conn.execute("INSERT OR IGNORE INTO seen (nonce) VALUES (?)", (nonce,))

    def __len__(self) -> int:
        with self._lock:
            return int(self._conn.execute("SELECT COUNT(*) FROM seen").fetchone()[0])


__all__ = ["PersistentNonces"]
