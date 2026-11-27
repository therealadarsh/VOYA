"""Copy rows from a SQLite file to SQLite or Postgres.

The target URL is never printed. Run: python -m voya.copy_db --from app.db --to "$DATABASE_URL"
"""

from __future__ import annotations

import argparse
import re
import sqlite3
import sys
from collections.abc import Sequence

import psycopg

from voya.db import DB

_NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def _tables(db: DB) -> list[str]:
    if db.postgres:
        sql = (
            "SELECT table_name AS name FROM information_schema.tables "
            "WHERE table_schema='public' AND table_type='BASE TABLE' ORDER BY table_name"
        )
    else:
        sql = (
            "SELECT name FROM sqlite_master WHERE type='table' "
            "AND name NOT LIKE 'sqlite_%' ORDER BY name"
        )
    with db.tx() as cursor:
        names = [str(row["name"]) for row in cursor.execute(sql)]
    return [name for name in names if name != "alembic_version" and _NAME.fullmatch(name)]


def _columns(db: DB, table: str) -> list[str]:
    if db.postgres:
        sql = (
            "SELECT column_name AS name FROM information_schema.columns "
            "WHERE table_schema='public' AND table_name=? ORDER BY ordinal_position"
        )
        with db.tx() as cursor:
            return [str(row["name"]) for row in cursor.execute(sql, (table,))]
    with db.tx() as cursor:
        return [str(row["name"]) for row in cursor.execute(f"PRAGMA table_info({table})")]


def _count(db: DB, table: str) -> int:
    with db.tx() as cursor:
        row = cursor.execute(f"SELECT COUNT(*) AS n FROM {table}").fetchone()
    if row is None:
        return 0
    return int(row["n"])


def _rows(db: DB, table: str, columns: Sequence[str]) -> list[tuple[object, ...]]:
    listed = ", ".join(columns)
    with db.tx() as cursor:
        return [
            tuple(row[name] for name in columns)
            for row in cursor.execute(f"SELECT {listed} FROM {table}")
        ]


class _OpenFailed(Exception):
    pass


def _open(target: str) -> DB:
    try:
        return DB(target)
    except (sqlite3.Error, psycopg.Error, OSError):
        print("Could not open the target database.", file=sys.stderr)
        raise _OpenFailed from None


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Copy rows from a SQLite file.")
    parser.add_argument("--from", dest="source", required=True)
    parser.add_argument("--to", dest="target", required=True)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args(list(argv) if argv is not None else None)
    if str(args.source).startswith("postgres"):
        print("The source must be a SQLite file.", file=sys.stderr)
        return 2
    source = DB(str(args.source))
    try:
        try:
            target = _open(str(args.target))
        except _OpenFailed:
            return 2
        try:
            return _copy(source, target, dry_run=bool(args.dry_run), force=bool(args.force))
        finally:
            target.close()
    finally:
        source.close()


def _copy(source: DB, target: DB, *, dry_run: bool, force: bool) -> int:
    tables = _tables(source)
    for table in tables:
        print(f"{table} {_count(source, table)}")
    if any(_count(target, table) for table in _tables(target)) and not force:
        print(
            "The target already has data. Re-run with --force to copy over it.",
            file=sys.stderr,
        )
        return 1
    if dry_run:
        print("Dry run. Nothing was copied.")
        return 0
    for table in tables:
        columns = _columns(source, table)
        rows = _rows(source, table, columns)
        listed = ", ".join(columns)
        marks = ", ".join("?" for _ in columns)
        with target.tx() as cursor:
            if force:
                cursor.execute(f"DELETE FROM {table}")
            for values in rows:
                cursor.execute(f"INSERT INTO {table} ({listed}) VALUES ({marks})", values)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
