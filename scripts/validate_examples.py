"""Validate examples/**/*.json when present (stub-friendly for M1)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EX = ROOT / "examples"


def main() -> int:
    if not EX.exists():
        print("validate_examples: no examples/ yet (ok)")
        return 0
    bad = 0
    for path in EX.rglob("*.json"):
        try:
            json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            print(f"{path}: {e}")
            bad += 1
    if bad:
        return 1
    print("validate_examples: ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
