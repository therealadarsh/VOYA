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
            raw = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            print(f"{path}: {e}")
            bad += 1
            continue
        if "destination" in raw and "start_date" in raw:
            from datetime import date
            from decimal import Decimal

            from voya.planner import PlanRequest

            kw = dict(raw)
            if isinstance(kw.get("start_date"), str):
                y, m, d = kw["start_date"].split("-")
                kw["start_date"] = date(int(y), int(m), int(d))
            if isinstance(kw.get("budget"), str):
                kw["budget"] = Decimal(kw["budget"])
            try:
                PlanRequest(**kw)
            except (ValueError, TypeError) as e:
                print(f"{path}: PlanRequest validation: {e}")
                bad += 1
    if bad:
        return 1
    print("validate_examples: ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
