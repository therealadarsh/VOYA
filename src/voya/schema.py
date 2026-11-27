"""Is the database at the Alembic head revision?"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import psycopg

from voya.db import DB


def alembic_ini() -> Path:
    candidates = (Path.cwd() / "alembic.ini", Path(__file__).resolve().parents[2] / "alembic.ini")
    for path in candidates:
        if path.is_file():
            return path
    return candidates[0]


def head_revision() -> str:
    from alembic.config import Config
    from alembic.script import ScriptDirectory

    head = ScriptDirectory.from_config(Config(str(alembic_ini()))).get_current_head()
    if head is None:
        raise RuntimeError("No database migration is defined.")
    return head


def current_revision(target: str) -> str | None:
    """Return the stamped revision, or None when the database has not been migrated."""
    db = DB(target)
    try:
        with db.tx() as cursor:
            row = cursor.execute("SELECT version_num FROM alembic_version").fetchone()
        if row is None:
            return None
        return str(row["version_num"])
    except (sqlite3.Error, psycopg.Error, OSError):
        # A missing alembic_version table means the database has not been migrated.
        return None
    finally:
        db.close()


def upgrade_to_head() -> None:
    """Apply migrations to the database chosen by VOYA_DB, DATABASE_URL, or VOYA_DATA_DIR."""
    from alembic import command
    from alembic.config import Config

    command.upgrade(Config(str(alembic_ini())), "head")
