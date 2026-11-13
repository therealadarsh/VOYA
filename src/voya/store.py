"""Persistence (SQLite for the MVP; same shape moves to Postgres later).

Plans are stored as their *request* (the planner is deterministic), with a
version history so changes can be undone. Spend entries store only amount,
category, day, trip and an optional plan line: no locations, no receipts.
"""

from __future__ import annotations

import hashlib
import json
import os
import secrets
import sqlite3
import threading
from contextlib import contextmanager
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Iterator

SCHEMA = """
CREATE TABLE IF NOT EXISTS plans (
  id TEXT PRIMARY KEY, owner TEXT, created_at TEXT NOT NULL, opened_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS plan_versions (
  plan_id TEXT NOT NULL, version INTEGER NOT NULL, request_json TEXT NOT NULL,
  reason TEXT NOT NULL, created_at TEXT NOT NULL, PRIMARY KEY (plan_id, version)
);
CREATE TABLE IF NOT EXISTS users (
  token_hash TEXT PRIMARY KEY, email_hash TEXT NOT NULL, adult_attested INTEGER NOT NULL,
  created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS preferences (
  owner TEXT NOT NULL, key TEXT NOT NULL, value TEXT NOT NULL, source TEXT NOT NULL,
  updated_at TEXT NOT NULL, PRIMARY KEY (owner, key)
);
CREATE TABLE IF NOT EXISTS spends (
  id TEXT PRIMARY KEY, plan_id TEXT NOT NULL, amount TEXT NOT NULL, category TEXT NOT NULL,
  line_id TEXT, note TEXT, day INTEGER, idem_key TEXT NOT NULL, created_at TEXT NOT NULL,
  UNIQUE (plan_id, idem_key)
);
CREATE TABLE IF NOT EXISTS proposals (
  id TEXT PRIMARY KEY, plan_id TEXT NOT NULL, base_version INTEGER NOT NULL,
  request_json TEXT NOT NULL, summary TEXT NOT NULL, delta TEXT NOT NULL,
  raises_total INTEGER NOT NULL, token_hash TEXT NOT NULL, used INTEGER NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS ai_spend (
  scope TEXT PRIMARY KEY, usd TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS magic_links (
  token_hash TEXT PRIMARY KEY, email TEXT NOT NULL, expires_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS feedback (
  id TEXT PRIMARY KEY, message TEXT NOT NULL, contact TEXT, created_at TEXT NOT NULL
);
"""


def default_db_path() -> str:
    explicit = os.environ.get("VOYA_DB")
    if explicit:
        return explicit
    return str(Path(os.environ.get("VOYA_DATA_DIR", "var")) / "voya.db")


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def _hash(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def new_id(prefix: str) -> str:
    return f"{prefix}_{secrets.token_urlsafe(8)}"


class Store:
    def __init__(self, path: str | None = None) -> None:
        self.path = path or default_db_path()
        if self.path != ":memory:":
            Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self.path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._lock = threading.Lock()
        with self._lock:
            self._conn.executescript(SCHEMA)

    def ping(self) -> None:
        with self.tx() as c:
            c.execute("SELECT 1")

    def add_feedback(self, message: str, contact: str | None) -> str:
        fid = new_id("fbk")
        with self.tx() as c:
            c.execute(
                "INSERT INTO feedback VALUES (?,?,?,?)",
                (fid, message, contact, _now()),
            )
        return fid

    def feedback_all(self) -> list[dict]:
        with self.tx() as c:
            return [dict(r) for r in c.execute("SELECT * FROM feedback ORDER BY created_at")]

    @contextmanager
    def tx(self) -> Iterator[sqlite3.Connection]:
        with self._lock:
            try:
                yield self._conn
                self._conn.commit()
            except Exception:
                self._conn.rollback()
                raise

    # -- plans ---------------------------------------------------------------
    def create_plan(self, request_json: str, owner: str | None = None) -> str:
        pid = new_id("pln")
        with self.tx() as c:
            c.execute("INSERT INTO plans VALUES (?,?,?,?)", (pid, owner, _now(), _now()))
            c.execute(
                "INSERT INTO plan_versions VALUES (?,?,?,?,?)",
                (pid, 1, request_json, "created", _now()),
            )
        return pid

    def plan(self, pid: str) -> dict | None:
        with self.tx() as c:
            row = c.execute("SELECT * FROM plans WHERE id=?", (pid,)).fetchone()
            if not row:
                return None
            ver = c.execute(
                "SELECT * FROM plan_versions WHERE plan_id=? ORDER BY version DESC LIMIT 1", (pid,)
            ).fetchone()
            c.execute("UPDATE plans SET opened_at=? WHERE id=?", (_now(), pid))
        return {
            "id": pid,
            "owner": row["owner"],
            "version": ver["version"],
            "request_json": ver["request_json"],
        }

    def add_version(self, pid: str, request_json: str, reason: str) -> int:
        with self.tx() as c:
            v = c.execute(
                "SELECT MAX(version) FROM plan_versions WHERE plan_id=?", (pid,)
            ).fetchone()[0]
            c.execute(
                "INSERT INTO plan_versions VALUES (?,?,?,?,?)",
                (pid, v + 1, request_json, reason, _now()),
            )
        return v + 1

    def undo(self, pid: str) -> bool:
        with self.tx() as c:
            v = c.execute(
                "SELECT MAX(version) FROM plan_versions WHERE plan_id=?", (pid,)
            ).fetchone()[0]
            if not v or v <= 1:
                return False
            c.execute("DELETE FROM plan_versions WHERE plan_id=? AND version=?", (pid, v))
        return True

    def claim(self, pid: str, owner: str) -> bool:
        with self.tx() as c:
            cur = c.execute(
                "UPDATE plans SET owner=? WHERE id=? AND (owner IS NULL OR owner=?)",
                (owner, pid, owner),
            )
        return cur.rowcount == 1

    def plans_for(self, owner: str) -> list[str]:
        with self.tx() as c:
            return [
                r["id"]
                for r in c.execute(
                    "SELECT id FROM plans WHERE owner=? ORDER BY created_at DESC", (owner,)
                )
            ]

    # -- users ---------------------------------------------------------------
    def save_magic_link(self, email: str, token: str, expires: datetime) -> None:
        em = email.strip().lower()
        with self.tx() as c:
            c.execute(
                "INSERT OR REPLACE INTO magic_links VALUES (?,?,?)",
                (_hash(token), em, expires.isoformat(timespec="seconds")),
            )

    def consume_magic_link(self, token: str) -> str | None:
        h = _hash(token)
        with self.tx() as c:
            row = c.execute(
                "SELECT email, expires_at FROM magic_links WHERE token_hash=?", (h,)
            ).fetchone()
            if not row:
                return None
            if datetime.fromisoformat(row["expires_at"]) < datetime.now(UTC):
                c.execute("DELETE FROM magic_links WHERE token_hash=?", (h,))
                return None
            email = row["email"]
            c.execute("DELETE FROM magic_links WHERE token_hash=?", (h,))
        return email

    def create_user(self, email: str, adult: bool) -> str:
        token = secrets.token_urlsafe(24)
        with self.tx() as c:
            c.execute(
                "INSERT INTO users VALUES (?,?,?,?)",
                (_hash(token), _hash(email.strip().lower()), int(adult), _now()),
            )
        return token

    def owner_for(self, token: str | None) -> str | None:
        if not token:
            return None
        h = _hash(token)
        with self.tx() as c:
            row = c.execute("SELECT token_hash FROM users WHERE token_hash=?", (h,)).fetchone()
        return h if row else None

    def delete_owner(self, owner: str) -> None:
        with self.tx() as c:
            ids = [r[0] for r in c.execute("SELECT id FROM plans WHERE owner=?", (owner,))]
            for pid in ids:
                for table in ("plan_versions", "spends", "proposals"):
                    c.execute(f"DELETE FROM {table} WHERE plan_id=?", (pid,))
            c.execute("DELETE FROM plans WHERE owner=?", (owner,))
            c.execute("DELETE FROM preferences WHERE owner=?", (owner,))
            c.execute("DELETE FROM users WHERE token_hash=?", (owner,))

    # -- preferences (memory) --------------------------------------------------
    def set_pref(self, owner: str, key: str, value: str, source: str) -> None:
        with self.tx() as c:
            c.execute(
                "INSERT OR REPLACE INTO preferences VALUES (?,?,?,?,?)",
                (owner, key, value, source, _now()),
            )

    def prefs(self, owner: str) -> list[dict]:
        with self.tx() as c:
            return [
                dict(r)
                for r in c.execute(
                    "SELECT key, value, source, updated_at FROM preferences WHERE owner=?", (owner,)
                )
            ]

    def forget_pref(self, owner: str, key: str) -> None:
        with self.tx() as c:
            c.execute("DELETE FROM preferences WHERE owner=? AND key=?", (owner, key))

    # -- spends --------------------------------------------------------------
    def add_spend(
        self,
        pid: str,
        amount: Decimal,
        category: str,
        line_id: str | None,
        note: str | None,
        day: int | None,
        idem_key: str,
    ) -> tuple[dict, bool]:
        with self.tx() as c:
            row = c.execute(
                "SELECT * FROM spends WHERE plan_id=? AND idem_key=?", (pid, idem_key)
            ).fetchone()
            if row:
                return dict(row), False
            sid = new_id("spd")
            c.execute(
                "INSERT INTO spends VALUES (?,?,?,?,?,?,?,?,?)",
                (
                    sid,
                    pid,
                    str(amount),
                    category,
                    line_id,
                    (note or "")[:120],
                    day,
                    idem_key,
                    _now(),
                ),
            )
            return dict(c.execute("SELECT * FROM spends WHERE id=?", (sid,)).fetchone()), True

    def spends(self, pid: str) -> list[dict]:
        with self.tx() as c:
            return [
                dict(r)
                for r in c.execute(
                    "SELECT * FROM spends WHERE plan_id=? ORDER BY created_at", (pid,)
                )
            ]

    def delete_spend(self, pid: str, sid: str) -> bool:
        with self.tx() as c:
            return (
                c.execute("DELETE FROM spends WHERE plan_id=? AND id=?", (pid, sid)).rowcount == 1
            )

    # -- proposals -------------------------------------------------------------
    def add_proposal(
        self,
        pid: str,
        base_version: int,
        request_json: str,
        summary: str,
        delta: Decimal,
        raises: bool,
    ) -> tuple[str, str]:
        prop_id, token = new_id("prp"), secrets.token_urlsafe(16)
        bound = _hash(token + request_json)
        with self.tx() as c:
            c.execute(
                "INSERT INTO proposals VALUES (?,?,?,?,?,?,?,?,0,?)",
                (
                    prop_id,
                    pid,
                    base_version,
                    request_json,
                    summary,
                    str(delta),
                    int(raises),
                    bound,
                    _now(),
                ),
            )
        return prop_id, token

    def take_proposal(self, pid: str, prop_id: str, token: str) -> dict | None:
        """Single-use: returns the proposal once if the token matches its content."""
        with self.tx() as c:
            row = c.execute(
                "SELECT * FROM proposals WHERE id=? AND plan_id=?", (prop_id, pid)
            ).fetchone()
            if not row or row["used"] or _hash(token + row["request_json"]) != row["token_hash"]:
                return None
            c.execute("UPDATE proposals SET used=1 WHERE id=?", (prop_id,))
            return dict(row)

    # -- AI spend counters -------------------------------------------------------
    def ai_spent(self, scope: str) -> Decimal:
        with self.tx() as c:
            row = c.execute("SELECT usd FROM ai_spend WHERE scope=?", (scope,)).fetchone()
        return Decimal(row["usd"]) if row else Decimal(0)

    def add_ai_spend(self, scope: str, usd: Decimal) -> None:
        with self.tx() as c:
            row = c.execute("SELECT usd FROM ai_spend WHERE scope=?", (scope,)).fetchone()
            total = (Decimal(row["usd"]) if row else Decimal(0)) + usd
            c.execute("INSERT OR REPLACE INTO ai_spend VALUES (?,?)", (scope, str(total)))


def dumps(obj: object) -> str:
    return json.dumps(obj, sort_keys=True, default=str)
