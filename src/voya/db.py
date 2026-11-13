"""SQLite or Postgres behind one cursor API (`?` placeholders).

`DATABASE_URL` starting with `postgres` selects Postgres. Everything else is a
SQLite path, including `:memory:`.
"""

from __future__ import annotations

import sqlite3
import threading
from collections.abc import Iterator, Mapping, Sequence
from contextlib import contextmanager
from pathlib import Path
from typing import Any

_UPSERTS = {
    "INSERT OR REPLACE INTO magic_links VALUES (?,?,?)": (
        "INSERT INTO magic_links (token_hash, email, expires_at) VALUES (%s,%s,%s) "
        "ON CONFLICT (token_hash) DO UPDATE SET email = EXCLUDED.email, "
        "expires_at = EXCLUDED.expires_at"
    ),
    "INSERT OR REPLACE INTO preferences VALUES (?,?,?,?,?)": (
        "INSERT INTO preferences (owner, key, value, source, updated_at) "
        "VALUES (%s,%s,%s,%s,%s) ON CONFLICT (owner, key) DO UPDATE SET "
        "value = EXCLUDED.value, source = EXCLUDED.source, updated_at = EXCLUDED.updated_at"
    ),
    "INSERT OR REPLACE INTO ai_spend VALUES (?,?)": (
        "INSERT INTO ai_spend (scope, usd) VALUES (%s,%s) "
        "ON CONFLICT (scope) DO UPDATE SET usd = EXCLUDED.usd"
    ),
}


def is_postgres(target: str) -> bool:
    return target.startswith("postgres")


def prepare_sql(sql: str, *, postgres: bool) -> str:
    if not postgres:
        return sql
    if sql in _UPSERTS:
        return _UPSERTS[sql]
    return sql.replace("?", "%s")


class Row(Mapping[str, Any]):
    def __init__(self, keys: Sequence[str], values: Sequence[Any]) -> None:
        self._keys = list(keys)
        self._values = list(values)

    def __getitem__(self, key: str | int) -> Any:
        if isinstance(key, int):
            return self._values[key]
        return self._values[self._keys.index(key)]

    def __iter__(self) -> Iterator[str]:
        return iter(self._keys)

    def __len__(self) -> int:
        return len(self._keys)


def _wrap(row: Any) -> Row | None:
    if row is None:
        return None
    if isinstance(row, sqlite3.Row):
        return Row(list(row.keys()), tuple(row))
    if isinstance(row, Mapping):
        return Row(list(row.keys()), list(row.values()))
    return Row([str(i) for i in range(len(row))], list(row))


class Result:
    def __init__(self, cursor: Any) -> None:
        self._cursor = cursor
        self.rowcount = int(cursor.rowcount)

    def fetchone(self) -> Row | None:
        return _wrap(self._cursor.fetchone())

    def __iter__(self) -> Iterator[Row]:
        for row in self._cursor.fetchall():
            wrapped = _wrap(row)
            if wrapped is not None:
                yield wrapped


class DB:
    def __init__(self, target: str) -> None:
        self.target = target
        self.postgres = is_postgres(target)
        self._lock = threading.Lock()
        if self.postgres:
            import psycopg
            from psycopg.rows import dict_row

            url = target.replace("postgresql+psycopg://", "postgresql://", 1)
            self._conn: Any = psycopg.connect(url, row_factory=dict_row)
        else:
            if target != ":memory:":
                Path(target).parent.mkdir(parents=True, exist_ok=True)
            conn = sqlite3.connect(target, check_same_thread=False)
            conn.row_factory = sqlite3.Row
            self._conn = conn

    def script(self, schema: str) -> None:
        statements = [part.strip() for part in schema.split(";") if part.strip()]
        with self._lock:
            for statement in statements:
                self._conn.execute(prepare_sql(statement, postgres=self.postgres))
            self._conn.commit()

    @contextmanager
    def tx(self) -> Iterator[ResultCursor]:
        with self._lock:
            try:
                yield ResultCursor(self)
                self._conn.commit()
            except Exception:
                self._conn.rollback()
                raise

    def close(self) -> None:
        self._conn.close()


class ResultCursor:
    def __init__(self, db: DB) -> None:
        self._db = db

    def execute(self, sql: str, params: Sequence[Any] = ()) -> Result:
        cursor = self._db._conn.execute(prepare_sql(sql, postgres=self._db.postgres), params)
        return Result(cursor)
