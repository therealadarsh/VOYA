"""Tracing: one trace per request, one span per step, written as JSONL.

Redaction happens before anything is written: coordinates are rounded to 3
decimals, free text is truncated, and keys that could hold secrets or personal
data are dropped. View traces with `python -m voya.obs show <trace_id>`.
"""

from __future__ import annotations

import contextvars
import json
import os
import secrets
import sys
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

_trace_id: contextvars.ContextVar[str | None] = contextvars.ContextVar("trace_id", default=None)
DROP_KEYS = {"email", "token", "api_key", "authorization", "password", "receipt_text"}
COORD_KEYS = {"lat", "lng", "latitude", "longitude"}


def trace_dir() -> Path:
    return Path(os.environ.get("VOYA_TRACE_DIR", "var/traces"))


def redact(value: Any, key: str = "") -> Any:
    if key.lower() in DROP_KEYS:
        return "[redacted]"
    if key.lower() in COORD_KEYS and isinstance(value, (int, float)):
        return round(float(value), 3)
    if isinstance(value, dict):
        return {k: redact(v, k) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [redact(v, key) for v in value][:50]
    if isinstance(value, str):
        return value if len(value) <= 200 else value[:200] + "…"
    if isinstance(value, float):
        return round(value, 6)
    return value


def new_trace() -> str:
    tid = f"trc_{secrets.token_hex(6)}"
    _trace_id.set(tid)
    return tid


def current_trace() -> str | None:
    return _trace_id.get()


def _write(record: dict) -> None:
    if os.environ.get("VOYA_TRACE", "1") == "0":
        return
    d = trace_dir()
    d.mkdir(parents=True, exist_ok=True)
    with (d / "traces.jsonl").open("a") as f:
        f.write(json.dumps(redact(record), default=str) + "\n")


@contextmanager
def span(name: str, **attrs: Any) -> Iterator[dict]:
    """Record a step. Callers may add result attributes to the yielded dict."""
    tid = current_trace() or new_trace()
    extra: dict = {}
    start = time.perf_counter()
    status = "ok"
    try:
        yield extra
    except Exception as e:
        status = f"error:{type(e).__name__}"
        raise
    finally:
        _write({"trace_id": tid, "span": name, "ms": round((time.perf_counter() - start) * 1000, 1),
                "status": status, **attrs, **extra})


def event(name: str, **attrs: Any) -> None:
    _write({"trace_id": current_trace(), "span": name, "ms": 0, "status": "ok", **attrs})


def load(trace_id: str) -> list[dict]:
    path = trace_dir() / "traces.jsonl"
    if not path.exists():
        return []
    out = []
    for line in path.read_text().splitlines():
        rec = json.loads(line)
        if rec.get("trace_id") == trace_id:
            out.append(rec)
    return out


def main(argv: list[str]) -> int:
    if len(argv) >= 2 and argv[0] == "show":
        for rec in load(argv[1]):
            attrs = {k: v for k, v in rec.items() if k not in ("trace_id", "span", "ms", "status")}
            print(f"{rec['span']:<18} {rec['ms']:>7} ms  {rec['status']:<8} {json.dumps(attrs)[:160]}")
        return 0
    if argv and argv[0] == "list":
        path = trace_dir() / "traces.jsonl"
        seen: dict[str, str] = {}
        for line in path.read_text().splitlines() if path.exists() else []:
            rec = json.loads(line)
            seen.setdefault(rec.get("trace_id") or "-", rec["span"])
        for tid, first in list(seen.items())[-30:]:
            print(tid, first)
        return 0
    print("usage: python -m voya.obs show <trace_id> | list")
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
