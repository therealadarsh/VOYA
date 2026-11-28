"""SQLite copy, and a Postgres copy when CI provides a database URL."""

from __future__ import annotations

import os
from pathlib import Path

import psycopg
import pytest

from voya.copy_db import main
from voya.db import DB
from voya.store import Store


def test_sqlite_copy_counts_rows_and_refuses_a_full_target(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    source = tmp_path / "source.db"
    target = tmp_path / "target.db"
    Store(str(source)).add_feedback("bring this row", None)
    Store(str(target))
    assert main(["--from", str(source), "--to", str(target), "--dry-run"]) == 0
    dry = capsys.readouterr()
    assert "feedback 1" in dry.out
    assert "Dry run" in dry.out
    assert str(target) not in dry.out + dry.err
    assert Store(str(target)).feedback_all() == []
    assert main(["--from", str(source), "--to", str(target)]) == 0
    assert Store(str(target)).feedback_all()[0]["message"] == "bring this row"
    refused = main(["--from", str(source), "--to", str(target)])
    err = capsys.readouterr()
    assert refused == 1
    assert "already has data" in err.err
    assert main(["--from", str(source), "--to", str(target), "--force"]) == 0
    assert len(Store(str(target)).feedback_all()) == 1


def test_a_missing_source_file_is_refused(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    missing = tmp_path / "typo.db"
    target = tmp_path / "target.db"
    Store(str(target))
    assert main(["--from", str(missing), "--to", str(target)]) == 2
    assert "does not exist" in capsys.readouterr().err
    assert not missing.exists()


def test_a_failed_open_does_not_print_the_url(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    source = tmp_path / "source.db"
    Store(str(source))
    secret = "postgresql://user:secret-token@db.example/voya"
    real = DB

    def open_db(target: str) -> DB:
        if "secret-token" in target:
            raise psycopg.OperationalError(target)
        return real(target)

    monkeypatch.setattr("voya.copy_db.DB", open_db)
    assert main(["--from", str(source), "--to", secret]) == 2
    captured = capsys.readouterr()
    assert "secret-token" not in captured.out + captured.err
    assert secret not in captured.out + captured.err


def test_postgres_copy_when_configured(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    url = os.environ.get("VOYA_TEST_DATABASE_URL", "")
    if not url.startswith("postgres"):
        pytest.skip("set VOYA_TEST_DATABASE_URL to a Postgres URL")
    source = tmp_path / "source.db"
    Store(str(source)).add_feedback("copied to postgres", None)
    target = DB(url)
    try:
        with target.tx() as cursor:
            for row in cursor.execute(
                "SELECT table_name AS name FROM information_schema.tables "
                "WHERE table_schema='public' AND table_type='BASE TABLE'"
            ):
                name = str(row["name"])
                if name != "alembic_version" and name.replace("_", "").isalnum():
                    cursor.execute(f"DELETE FROM {name}")
    finally:
        target.close()
    assert main(["--from", str(source), "--to", url]) == 0
    captured = capsys.readouterr()
    assert url not in captured.out + captured.err
    assert "postgres" not in captured.out.lower()
    again = Store(url)
    assert again.feedback_all()[0]["message"] == "copied to postgres"
    with again.tx() as cursor:
        cursor.execute("DELETE FROM feedback")
