"""Process logs. Access lines keep the path and drop the query string."""

from __future__ import annotations

import json
import logging
from typing import Any


def request_path(path: str) -> str:
    """Return the URL path with any query string removed."""
    return path.split("?", 1)[0]


class JsonFormatter(logging.Formatter):
    _FIELDS = ("method", "path", "status_code", "trace_id", "duration_ms")

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for key in self._FIELDS:
            if hasattr(record, key):
                payload[key] = getattr(record, key)
        return json.dumps(payload, default=str)


def configure_logging(*, json_logs: bool) -> None:
    log = logging.getLogger("voya")
    log.setLevel(logging.INFO)
    log.handlers.clear()
    handler = logging.StreamHandler()
    handler.setFormatter(
        JsonFormatter() if json_logs else logging.Formatter("%(levelname)s %(message)s")
    )
    log.addHandler(handler)
    log.propagate = False


def access_log(
    *,
    method: str,
    path: str,
    status_code: int,
    trace_id: str,
    duration_ms: int,
) -> None:
    logging.getLogger("voya.access").info(
        "request",
        extra={
            "method": method,
            "path": request_path(path),
            "status_code": status_code,
            "trace_id": trace_id,
            "duration_ms": duration_ms,
        },
    )
