"""Durable state for the demo path (SQLite, one file per service).

* :class:`SessionStore` (orchestration): one session per alert, keyed by an idempotency
  key; every planned evidence request and its response; the incident card; analyst
  actions with four-eyes approval for high-impact ones. A crashed or restarted
  orchestrator resumes a session from here and never re-sends an answered request.
* :class:`BudgetLedger` (token service): evaluations used per bank and epoch, and a log
  of every call, so a restart does not reset the OPRF query budget. The privacy ledger
  (week 16) reads both.

Each write is one transaction; WAL mode lets the console read while a service writes.
"""

from __future__ import annotations

import json
import sqlite3
import threading
import time
from pathlib import Path
from typing import Any

HIGH_IMPACT = frozenset({"escalate", "freeze_account", "file_report"})
TERMINAL = frozenset({"closed", "failed"})

_SESSION_SCHEMA = """
CREATE TABLE IF NOT EXISTS sessions (
    key TEXT PRIMARY KEY, member INTEGER NOT NULL, window INTEGER NOT NULL,
    state TEXT NOT NULL, attempts INTEGER NOT NULL DEFAULT 0, error TEXT,
    card TEXT, created REAL NOT NULL, updated REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS requests (
    session TEXT NOT NULL, idx INTEGER NOT NULL, responder INTEGER NOT NULL,
    epoch INTEGER NOT NULL, request TEXT NOT NULL, response TEXT, status TEXT NOT NULL,
    sent REAL, answered REAL, PRIMARY KEY (session, idx)
);
CREATE TABLE IF NOT EXISTS actions (
    id INTEGER PRIMARY KEY AUTOINCREMENT, session TEXT NOT NULL, action TEXT NOT NULL,
    actor TEXT NOT NULL, status TEXT NOT NULL, approver TEXT, note TEXT,
    created REAL NOT NULL, decided REAL
);
"""
_BUDGET_SCHEMA = """
CREATE TABLE IF NOT EXISTS usage (
    bank INTEGER NOT NULL, epoch INTEGER NOT NULL, used INTEGER NOT NULL,
    PRIMARY KEY (bank, epoch)
);
CREATE TABLE IF NOT EXISTS calls (
    ts REAL NOT NULL, bank INTEGER NOT NULL, epoch INTEGER NOT NULL,
    evaluated INTEGER NOT NULL, refused INTEGER NOT NULL
);
"""


class _Db:
    def __init__(self, path: Path | str, schema: str) -> None:
        self.path = str(path)
        if self.path != ":memory:":
            Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.path, check_same_thread=False, timeout=30)
        self.conn.row_factory = sqlite3.Row
        self.lock = threading.RLock()
        with self.lock:
            if self.path != ":memory:":
                self.conn.execute("PRAGMA journal_mode=WAL")
            self.conn.execute("PRAGMA foreign_keys=ON")
            self.conn.executescript(schema)

    def close(self) -> None:
        with self.lock:
            self.conn.close()


class SessionStore(_Db):
    def __init__(self, path: Path | str) -> None:
        super().__init__(path, _SESSION_SCHEMA)

    # ------------------------------------------------------------------ sessions
    def open(self, key: str, member: int, window: int) -> tuple[dict[str, Any], bool]:
        """The session for ``key``, created if new; (row, created)."""
        now = time.time()
        with self.lock, self.conn:
            cur = self.conn.execute(
                "INSERT OR IGNORE INTO sessions (key, member, window, state, created, updated) "
                "VALUES (?, ?, ?, 'opened', ?, ?)",
                (key, member, window, now, now),
            )
            created = cur.rowcount == 1
        return self.session(key), created

    def session(self, key: str) -> dict[str, Any]:
        with self.lock:
            row = self.conn.execute("SELECT * FROM sessions WHERE key = ?", (key,)).fetchone()
        if row is None:
            raise KeyError(key)
        out = dict(row)
        out["card"] = json.loads(out["card"]) if out["card"] else None
        return out

    def sessions(self, member: int | None = None) -> list[dict[str, Any]]:
        q = "SELECT key FROM sessions"
        args: tuple[int, ...] = ()
        if member is not None:
            q, args = q + " WHERE member = ?", (member,)
        with self.lock:
            keys = [r["key"] for r in self.conn.execute(q + " ORDER BY window, key", args)]
        return [self.session(k) for k in keys]

    def set_state(self, key: str, state: str, error: str | None = None) -> None:
        with self.lock, self.conn:
            self.conn.execute(
                "UPDATE sessions SET state = ?, error = ?, updated = ? WHERE key = ?",
                (state, error, time.time(), key),
            )

    def bump_attempt(self, key: str) -> int:
        with self.lock, self.conn:
            self.conn.execute(
                "UPDATE sessions SET attempts = attempts + 1, updated = ? WHERE key = ?",
                (time.time(), key),
            )
        return int(self.session(key)["attempts"])

    def close_with_card(self, key: str, card: dict[str, Any]) -> None:
        with self.lock, self.conn:
            self.conn.execute(
                "UPDATE sessions SET state = 'closed', card = ?, error = NULL, updated = ? "
                "WHERE key = ?",
                (json.dumps(card), time.time(), key),
            )

    # ------------------------------------------------------------------ requests
    def plan_requests(self, key: str, planned: list[tuple[int, int, dict[str, Any]]]) -> None:
        """Store every planned request (responder, epoch, encoded request) in one transaction,
        and move the session to 'planned'. Signed once: a resumed session reuses them."""
        with self.lock, self.conn:
            for idx, (responder, epoch, request) in enumerate(planned):
                self.conn.execute(
                    "INSERT OR IGNORE INTO requests (session, idx, responder, epoch, request, "
                    "status) VALUES (?, ?, ?, ?, ?, 'planned')",
                    (key, idx, responder, epoch, json.dumps(request)),
                )
            self.conn.execute(
                "UPDATE sessions SET state = 'planned', updated = ? WHERE key = ?",
                (time.time(), key),
            )

    def requests(self, key: str) -> list[dict[str, Any]]:
        with self.lock:
            rows = self.conn.execute(
                "SELECT * FROM requests WHERE session = ? ORDER BY idx", (key,)
            ).fetchall()
        out = []
        for r in rows:
            d = dict(r)
            d["request"] = json.loads(d["request"])
            d["response"] = json.loads(d["response"]) if d["response"] else None
            out.append(d)
        return out

    def all_requests(self) -> list[dict[str, Any]]:
        """Every request of every session, with its session's member (privacy ledger)."""
        with self.lock:
            rows = self.conn.execute(
                "SELECT r.*, s.member AS requester FROM requests r "
                "JOIN sessions s ON s.key = r.session ORDER BY r.session, r.idx"
            ).fetchall()
        out = []
        for r in rows:
            d = dict(r)
            d["request"] = json.loads(d["request"])
            d["response"] = json.loads(d["response"]) if d["response"] else None
            out.append(d)
        return out

    def mark_sent(self, key: str, idx: int) -> None:
        with self.lock, self.conn:
            self.conn.execute(
                "UPDATE requests SET status = 'sent', sent = ? WHERE session = ? AND idx = ?",
                (time.time(), key, idx),
            )

    def save_response(
        self, key: str, idx: int, status: str, response: dict[str, Any] | None
    ) -> None:
        with self.lock, self.conn:
            self.conn.execute(
                "UPDATE requests SET status = ?, response = ?, answered = ? "
                "WHERE session = ? AND idx = ?",
                (status, json.dumps(response) if response else None, time.time(), key, idx),
            )

    # ------------------------------------------------------------------ actions
    def record_action(self, key: str, action: str, actor: str, note: str = "") -> dict[str, Any]:
        """Low-impact actions are done at once; high-impact ones wait for a second person."""
        self.session(key)  # must exist
        status = "pending_approval" if action in HIGH_IMPACT else "done"
        with self.lock, self.conn:
            cur = self.conn.execute(
                "INSERT INTO actions (session, action, actor, status, note, created) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (key, action, actor, status, note, time.time()),
            )
        return self.action(int(cur.lastrowid or 0))

    def decide(self, action_id: int, approver: str, approve: bool) -> dict[str, Any]:
        a = self.action(action_id)
        if a["status"] != "pending_approval":
            raise ValueError(f"action {action_id} is not waiting for approval")
        if approver == a["actor"]:
            raise PermissionError("a high-impact action needs a second person to approve it")
        with self.lock, self.conn:
            self.conn.execute(
                "UPDATE actions SET status = ?, approver = ?, decided = ? WHERE id = ?",
                ("approved" if approve else "rejected", approver, time.time(), action_id),
            )
        return self.action(action_id)

    def action(self, action_id: int) -> dict[str, Any]:
        with self.lock:
            row = self.conn.execute("SELECT * FROM actions WHERE id = ?", (action_id,)).fetchone()
        if row is None:
            raise KeyError(action_id)
        return dict(row)

    def actions(self, key: str) -> list[dict[str, Any]]:
        with self.lock:
            rows = self.conn.execute(
                "SELECT * FROM actions WHERE session = ? ORDER BY id", (key,)
            ).fetchall()
        return [dict(r) for r in rows]


class BudgetLedger(_Db):
    """The token service's per-bank, per-epoch evaluation counts, kept across restarts."""

    def __init__(self, path: Path | str) -> None:
        super().__init__(path, _BUDGET_SCHEMA)

    def used(self, bank: int, epoch: int) -> int:
        with self.lock:
            row = self.conn.execute(
                "SELECT used FROM usage WHERE bank = ? AND epoch = ?", (bank, epoch)
            ).fetchone()
        return int(row["used"]) if row else 0

    def record(self, bank: int, epoch: int, evaluated: int, refused: int) -> None:
        with self.lock, self.conn:
            if evaluated:
                self.conn.execute(
                    "INSERT INTO usage (bank, epoch, used) VALUES (?, ?, ?) "
                    "ON CONFLICT (bank, epoch) DO UPDATE SET used = used + excluded.used",
                    (bank, epoch, evaluated),
                )
            self.conn.execute(
                "INSERT INTO calls (ts, bank, epoch, evaluated, refused) VALUES (?, ?, ?, ?, ?)",
                (time.time(), bank, epoch, evaluated, refused),
            )

    def calls(self) -> list[dict[str, Any]]:
        with self.lock:
            return [dict(r) for r in self.conn.execute("SELECT * FROM calls ORDER BY ts")]


__all__ = ["HIGH_IMPACT", "TERMINAL", "BudgetLedger", "SessionStore"]
