"""Alembic brings an empty database up to the schema the store expects."""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from voya import api as api_mod
from voya.db import DB
from voya.schema import current_revision, head_revision, upgrade_to_head
from voya.store import Store


def _columns(path: str) -> dict[str, list[tuple[str, str]]]:
    db = DB(path)
    try:
        with db.tx() as cursor:
            tables = [
                str(row["name"])
                for row in cursor.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
                )
            ]
            found: dict[str, list[tuple[str, str]]] = {}
            for table in tables:
                if not table.replace("_", "").isalnum():
                    continue
                found[table] = [
                    (str(row["name"]), str(row["type"]))
                    for row in cursor.execute(f"PRAGMA table_info({table})")
                ]
        return found
    finally:
        db.close()


def test_upgrade_matches_the_store(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    migrated = tmp_path / "migrated.db"
    monkeypatch.setenv("VOYA_DB", str(migrated))
    monkeypatch.delenv("DATABASE_URL", raising=False)
    upgrade_to_head()
    fresh = tmp_path / "store.db"
    Store(str(fresh))
    migrated_columns = _columns(str(migrated))
    store_columns = _columns(str(fresh))
    assert "alembic_version" in migrated_columns
    assert "idea_stats" in migrated_columns
    assert "ideas_json" in {name for name, _type in migrated_columns["plan_versions"]}
    del migrated_columns["alembic_version"]
    assert migrated_columns == store_columns
    assert current_revision(str(migrated)) == head_revision()


def test_production_refuses_an_unmigrated_database(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("VOYA_ENV", "production")
    monkeypatch.setenv("VOYA_INVITE_CODE", "preview-invite-1")
    monkeypatch.setenv("VOYA_PUBLIC_URL", "https://preview.example")
    monkeypatch.setenv("VOYA_DEV_SIGNIN", "0")
    monkeypatch.setenv("VOYA_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("VOYA_SMTP_HOST", "smtp.example")
    monkeypatch.setenv("VOYA_SMTP_PORT", "587")
    monkeypatch.setenv("VOYA_SMTP_USERNAME", "voya")
    monkeypatch.setenv("VOYA_SMTP_PASSWORD", "secret")
    monkeypatch.setenv("VOYA_SMTP_FROM", "sign-in@example.com")
    monkeypatch.setenv("VOYA_METRICS_TOKEN", "metrics-test-token")
    monkeypatch.setenv("VOYA_DB", str(tmp_path / "empty.db"))
    api_mod._state.clear()
    with pytest.raises(RuntimeError, match="make migrate"), TestClient(api_mod.app):
        pass


def test_postgres_migration_is_at_head() -> None:
    url = os.environ.get("VOYA_TEST_DATABASE_URL", "")
    if not url.startswith("postgres"):
        pytest.skip("set VOYA_TEST_DATABASE_URL to a Postgres URL")
    assert current_revision(url) == head_revision()
