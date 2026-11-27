"""Where the app puts its database. Blank lines copied from .env.example count as unset."""

from __future__ import annotations

from pathlib import Path

import pytest

from voya.store import default_db_path

DB_VARS = ("VOYA_DB", "DATABASE_URL", "VOYA_DATA_DIR")


@pytest.fixture
def clean_env(monkeypatch: pytest.MonkeyPatch) -> pytest.MonkeyPatch:
    for name in DB_VARS:
        monkeypatch.delenv(name, raising=False)
    return monkeypatch


def test_unset_uses_var_folder(clean_env: pytest.MonkeyPatch) -> None:
    assert default_db_path() == str(Path("var") / "voya.db")


def test_blank_values_use_var_folder(clean_env: pytest.MonkeyPatch) -> None:
    for name in DB_VARS:
        clean_env.setenv(name, "")
    assert default_db_path() == str(Path("var") / "voya.db")


def test_whitespace_data_dir_uses_var_folder(clean_env: pytest.MonkeyPatch) -> None:
    clean_env.setenv("VOYA_DATA_DIR", "   ")
    assert default_db_path() == str(Path("var") / "voya.db")


def test_data_dir_is_used(clean_env: pytest.MonkeyPatch, tmp_path: Path) -> None:
    clean_env.setenv("VOYA_DATA_DIR", str(tmp_path))
    assert default_db_path() == str(tmp_path / "voya.db")


def test_explicit_db_wins(clean_env: pytest.MonkeyPatch, tmp_path: Path) -> None:
    clean_env.setenv("VOYA_DB", str(tmp_path / "other.db"))
    clean_env.setenv("VOYA_DATA_DIR", str(tmp_path / "ignored"))
    assert default_db_path() == str(tmp_path / "other.db")


def test_postgres_url_is_used(clean_env: pytest.MonkeyPatch) -> None:
    clean_env.setenv("DATABASE_URL", "postgresql://db.example/voya")
    assert default_db_path() == "postgresql://db.example/voya"


def test_example_env_runs_on_sqlite_out_of_the_box() -> None:
    example = Path(__file__).resolve().parents[1] / ".env.example"
    values = dict(
        line.split("=", 1)
        for line in example.read_text().splitlines()
        if line and not line.startswith("#") and "=" in line
    )
    assert not values.get("DATABASE_URL", "").strip().startswith("postgres")
