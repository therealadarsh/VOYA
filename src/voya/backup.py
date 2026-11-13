"""Copy the SQLite database with the backup API so a redeploy can be restored."""

from __future__ import annotations

import os
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

from voya.settings import load_settings


def backup_sqlite(src: Path, dest_dir: Path, *, now: datetime | None = None) -> Path:
    """Write a consistent copy of `src` into `dest_dir`. Returns the new file."""
    if not src.is_file():
        raise FileNotFoundError(src)
    dest_dir.mkdir(parents=True, exist_ok=True)
    stamp = (now or datetime.now(UTC)).strftime("%Y%m%dT%H%M%SZ")
    dest = dest_dir / f"voya-{stamp}.db"
    source = sqlite3.connect(src)
    target = sqlite3.connect(dest)
    try:
        source.backup(target)
    finally:
        target.close()
        source.close()
    return dest


def main() -> int:
    settings = load_settings()
    src = Path(os.environ.get("VOYA_DB", str(settings.data_dir / "voya.db")))
    dest = backup_sqlite(src, settings.data_dir / "backups")
    print(dest)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
