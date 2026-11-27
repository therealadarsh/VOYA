"""Persistence (SQLite, or Postgres when `DATABASE_URL` is a postgres URL).

Plans are stored as their *request* (the planner is deterministic), with a
version history so changes can be undone. Spend entries store only amount,
category, day, trip and an optional plan line: no locations, no receipts.
"""

from __future__ import annotations

import hashlib
import json
import os
import secrets
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any

from voya.db import DB, ResultCursor

SCHEMA = """
CREATE TABLE IF NOT EXISTS plans (
  id TEXT PRIMARY KEY, owner TEXT, created_at TEXT NOT NULL, opened_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS plan_versions (
  plan_id TEXT NOT NULL, version INTEGER NOT NULL, request_json TEXT NOT NULL,
  reason TEXT NOT NULL, created_at TEXT NOT NULL, ideas_json TEXT NOT NULL DEFAULT 'null',
  PRIMARY KEY (plan_id, version)
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
CREATE TABLE IF NOT EXISTS signin_attempts (
  email_hash TEXT NOT NULL, attempted_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS idea_stats (
  option_id TEXT PRIMARY KEY,
  shown INTEGER NOT NULL DEFAULT 0,
  kept INTEGER NOT NULL DEFAULT 0,
  swapped INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS places (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  category TEXT NOT NULL,
  tags TEXT NOT NULL,
  lat TEXT NOT NULL,
  lng TEXT NOT NULL,
  hours TEXT,
  provider_ids TEXT NOT NULL,
  source TEXT NOT NULL,
  observed_at TEXT NOT NULL,
  cache_until TEXT NOT NULL
);
"""


def default_db_path() -> str:
    # A blank line copied from .env.example counts as unset, so the database
    # never lands in the working directory by accident.
    explicit = os.environ.get("VOYA_DB", "").strip()
    if explicit:
        return explicit
    url = os.environ.get("DATABASE_URL", "").strip()
    if url.startswith("postgres"):
        return url
    data_dir = os.environ.get("VOYA_DATA_DIR", "").strip() or "var"
    return str(Path(data_dir) / "voya.db")


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def _hash(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def new_id(prefix: str) -> str:
    return f"{prefix}_{secrets.token_urlsafe(8)}"


def _bump_idea(cursor: ResultCursor, option_id: str, field: str) -> None:
    """Add one to shown, kept, or swapped. The row has no user, plan, or address."""
    if field not in {"shown", "kept", "swapped"}:
        raise ValueError(field)
    shown = 1 if field == "shown" else 0
    kept = 1 if field == "kept" else 0
    swapped = 1 if field == "swapped" else 0
    cursor.execute(
        "INSERT INTO idea_stats (option_id, shown, kept, swapped) VALUES (?,?,?,?) "
        "ON CONFLICT (option_id) DO UPDATE SET "
        "shown = idea_stats.shown + excluded.shown, "
        "kept = idea_stats.kept + excluded.kept, "
        "swapped = idea_stats.swapped + excluded.swapped",
        (option_id, shown, kept, swapped),
    )


def _idea_seen(cursor: ResultCursor, plan_id: str, option_id: str) -> bool:
    from voya.ideas import option_ids

    rows = cursor.execute("SELECT ideas_json FROM plan_versions WHERE plan_id=?", (plan_id,))
    return any(option_id in option_ids(str(row["ideas_json"] or "")) for row in rows)


class Store:
    def __init__(self, path: str | None = None) -> None:
        self.path = path or default_db_path()
        self._db = DB(self.path)
        self._db.script(SCHEMA)

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

    def feedback_all(self) -> list[dict[str, Any]]:
        with self.tx() as c:
            return [dict(r) for r in c.execute("SELECT * FROM feedback ORDER BY created_at")]

    def upsert_place(self, place: dict[str, Any]) -> None:
        with self.tx() as cursor:
            cursor.execute(
                "INSERT INTO places (id, name, category, tags, lat, lng, hours, provider_ids, "
                "source, observed_at, cache_until) VALUES (?,?,?,?,?,?,?,?,?,?,?) "
                "ON CONFLICT (id) DO UPDATE SET "
                "name=excluded.name, category=excluded.category, tags=excluded.tags, "
                "lat=excluded.lat, lng=excluded.lng, hours=excluded.hours, "
                "provider_ids=excluded.provider_ids, source=excluded.source, "
                "observed_at=excluded.observed_at, cache_until=excluded.cache_until",
                (
                    place["id"],
                    place["name"],
                    place["category"],
                    place["tags"],
                    place["lat"],
                    place["lng"],
                    place["hours"],
                    place["provider_ids"],
                    place["source"],
                    place["observed_at"],
                    place["cache_until"],
                ),
            )

    def places(self) -> list[dict[str, Any]]:
        with self.tx() as cursor:
            return [dict(row) for row in cursor.execute("SELECT * FROM places ORDER BY id")]

    def delete_place(self, place_id: str) -> None:
        with self.tx() as cursor:
            cursor.execute("DELETE FROM places WHERE id=?", (place_id,))

    def signin_attempt_rows(self) -> list[dict[str, Any]]:
        """Counter rows. Each row holds a hash, never the address."""
        with self.tx() as c:
            return [
                dict(r) for r in c.execute("SELECT email_hash, attempted_at FROM signin_attempts")
            ]

    def record_signin_attempt(
        self, email: str, *, now: datetime, max_per_15min: int, max_per_day: int
    ) -> bool:
        """Record one sign-in email if both limits allow it.

        The key is a hash of the lower-cased address. Over the limit, nothing
        is inserted and the caller must not send mail.
        """
        digest = _hash(email.strip().lower())
        moment = now.astimezone(UTC)
        stamp = moment.isoformat(timespec="seconds")
        cutoff_15 = (moment - timedelta(minutes=15)).isoformat(timespec="seconds")
        cutoff_day = (moment - timedelta(days=1)).isoformat(timespec="seconds")
        with self.tx() as c:
            recent = c.execute(
                "SELECT COUNT(*) AS n FROM signin_attempts WHERE email_hash=? AND attempted_at>=?",
                (digest, cutoff_15),
            ).fetchone()
            today = c.execute(
                "SELECT COUNT(*) AS n FROM signin_attempts WHERE email_hash=? AND attempted_at>=?",
                (digest, cutoff_day),
            ).fetchone()
            per_15 = int(recent["n"]) if recent else 0
            per_day = int(today["n"]) if today else 0
            if per_15 >= max_per_15min or per_day >= max_per_day:
                return False
            c.execute(
                "INSERT INTO signin_attempts (email_hash, attempted_at) VALUES (?,?)",
                (digest, stamp),
            )
        return True

    @contextmanager
    def tx(self) -> Iterator[ResultCursor]:
        with self._db.tx() as cursor:
            yield cursor

    # -- plans ---------------------------------------------------------------
    def create_plan(self, request_json: str, owner: str | None = None) -> str:
        from voya.ideas import initial_ideas

        pid = new_id("pln")
        ideas_json, chosen = initial_ideas(pid, request_json)
        with self.tx() as c:
            c.execute("INSERT INTO plans VALUES (?,?,?,?)", (pid, owner, _now(), _now()))
            c.execute(
                "INSERT INTO plan_versions "
                "(plan_id, version, request_json, reason, created_at, ideas_json) "
                "VALUES (?,?,?,?,?,?)",
                (pid, 1, request_json, "created", _now(), ideas_json),
            )
            for option_id in chosen:
                _bump_idea(c, option_id, "shown")
        return pid

    def plan(self, pid: str) -> dict[str, Any] | None:
        with self.tx() as c:
            row = c.execute("SELECT * FROM plans WHERE id=?", (pid,)).fetchone()
            if row is None:
                return None
            ver = c.execute(
                "SELECT * FROM plan_versions WHERE plan_id=? ORDER BY version DESC LIMIT 1", (pid,)
            ).fetchone()
            if ver is None:
                return None
            c.execute("UPDATE plans SET opened_at=? WHERE id=?", (_now(), pid))
        return {
            "id": pid,
            "owner": row["owner"],
            "version": ver["version"],
            "request_json": ver["request_json"],
            "ideas_json": ver.get("ideas_json", "null"),
        }

    def add_version(
        self,
        pid: str,
        request_json: str,
        reason: str,
        ideas_json: str | None = None,
        *,
        left_id: str | None = None,
        arrived_id: str | None = None,
    ) -> int:
        with self.tx() as c:
            if ideas_json is None:
                current = c.execute(
                    "SELECT ideas_json FROM plan_versions WHERE plan_id=? "
                    "ORDER BY version DESC LIMIT 1",
                    (pid,),
                ).fetchone()
                ideas_json = (
                    str(current["ideas_json"])
                    if current and current["ideas_json"] is not None
                    else "null"
                )
            ver_row = c.execute(
                "SELECT MAX(version) FROM plan_versions WHERE plan_id=?", (pid,)
            ).fetchone()
            if ver_row is None:
                raise RuntimeError("plan_versions query returned no row")
            v = int(ver_row[0] or 0)
            first_time = bool(
                left_id
                and arrived_id
                and left_id != arrived_id
                and not _idea_seen(c, pid, arrived_id)
            )
            c.execute(
                "INSERT INTO plan_versions "
                "(plan_id, version, request_json, reason, created_at, ideas_json) "
                "VALUES (?,?,?,?,?,?)",
                (pid, v + 1, request_json, reason, _now(), ideas_json),
            )
            if left_id and arrived_id and left_id != arrived_id:
                _bump_idea(c, left_id, "swapped")
                if first_time:
                    _bump_idea(c, arrived_id, "shown")
        return v + 1

    def undo(self, pid: str) -> bool:
        with self.tx() as c:
            ver_row = c.execute(
                "SELECT MAX(version) FROM plan_versions WHERE plan_id=?", (pid,)
            ).fetchone()
            if ver_row is None:
                return False
            v = int(ver_row[0] or 0)
            if not v or v <= 1:
                return False
            c.execute("DELETE FROM plan_versions WHERE plan_id=? AND version=?", (pid, v))
        return True

    def mark_ideas_kept(self, pid: str) -> None:
        from voya.ideas import option_ids

        rec = self.plan(pid)
        if rec is None:
            return
        with self.tx() as c:
            for option_id in option_ids(str(rec.get("ideas_json") or "")):
                _bump_idea(c, option_id, "kept")

    def idea_stat_rows(self) -> list[dict[str, Any]]:
        with self.tx() as c:
            return [
                dict(row)
                for row in c.execute(
                    "SELECT option_id, shown, kept, swapped FROM idea_stats ORDER BY option_id"
                )
            ]

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
        return str(email)

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

    def prefs(self, owner: str) -> list[dict[str, Any]]:
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
    ) -> tuple[dict[str, Any], bool]:
        with self.tx() as c:
            row = c.execute(
                "SELECT * FROM spends WHERE plan_id=? AND idem_key=?", (pid, idem_key)
            ).fetchone()
            if row is not None:
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
            spend_row = c.execute("SELECT * FROM spends WHERE id=?", (sid,)).fetchone()
            if spend_row is None:
                raise RuntimeError("inserted spend row missing")
            return dict(spend_row), True

    def spends(self, pid: str) -> list[dict[str, Any]]:
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

    def take_proposal(self, pid: str, prop_id: str, token: str) -> dict[str, Any] | None:
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
