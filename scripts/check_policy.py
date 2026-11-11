"""Policy checks: banned words, coordinates, secrets patterns (plan section 11)."""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCAN_DIRS = ("src", "web", "data", "examples")
SKIP = {"reference", "docs/PLAN.md"}
BANNED = re.compile(r"\bguarante(e|ed)\b", re.IGNORECASE)
# Lat/lng use 2–3 digits before the decimal; tax rates like 0.1025 are not coordinates.
COORD = re.compile(r"-?\d{2,3}\.\d{4,}")
SECRET_PATTERNS = [
    re.compile(r"sk-[A-Za-z0-9]{20,}"),
    re.compile(r"OPENROUTER_API_KEY\s*=\s*['\"][^'\"]+['\"]"),
]


def iter_files() -> list[Path]:
    out: list[Path] = []
    for name in SCAN_DIRS:
        base = ROOT / name
        if not base.exists():
            continue
        for p in base.rglob("*"):
            if p.is_file() and p.suffix in {
                ".py",
                ".js",
                ".ts",
                ".tsx",
                ".json",
                ".md",
                ".html",
                ".css",
            }:
                out.append(p)
    readme = ROOT / "README.md"
    if readme.exists():
        out.append(readme)
    return out


def main() -> int:
    errors: list[str] = []
    for path in iter_files():
        text = path.read_text(encoding="utf-8", errors="replace")
        rel = path.relative_to(ROOT)
        for m in BANNED.finditer(text):
            line_start = text.rfind("\n", 0, m.start()) + 1
            line = text[line_start : text.find("\n", m.start())]
            if "re.compile" in line and "guarante" in line:
                continue
            errors.append(f"{rel}: banned word at col {m.start()}")
        for m in COORD.finditer(text):
            snippet = text[max(0, m.start() - 20) : m.end() + 20]
            if "test_" in str(rel) or "synthetic" in snippet:
                continue
            errors.append(f"{rel}: coordinate >3 dp: {m.group()}")
        for pat in SECRET_PATTERNS:
            if pat.search(text) and ".example" not in str(rel):
                errors.append(f"{rel}: possible secret pattern")
    if errors:
        print("\n".join(errors))
        return 1
    print("check_policy: ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
