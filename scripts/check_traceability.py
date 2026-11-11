"""Light traceability: ensure key situation IDs appear in tests (M1 subset)."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TESTS = ROOT / "tests"
REQUIRED_SNIPPETS = {
    "S-01": "infeasible",
    "S-23": "same_request_same_plan",
    "MVP-PLAN": "test_value_plan",
}


def main() -> int:
    blob = "\n".join(p.read_text(encoding="utf-8") for p in TESTS.glob("*.py"))
    missing = [k for k, needle in REQUIRED_SNIPPETS.items() if needle not in blob]
    if missing:
        print("check_traceability: missing hooks for", ", ".join(missing))
        return 1
    print("check_traceability: ok (M1 subset)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
