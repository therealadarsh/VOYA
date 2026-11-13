"""In-process request counters. Rendered as Prometheus text at `/metrics`."""

from __future__ import annotations

import threading


class Metrics:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.requests = 0
        self.errors = 0
        self.duration_ms = 0

    def observe(self, status_code: int, duration_ms: int) -> None:
        with self._lock:
            self.requests += 1
            if status_code >= 500:
                self.errors += 1
            self.duration_ms += duration_ms

    def render(self) -> str:
        with self._lock:
            requests, errors, duration = self.requests, self.errors, self.duration_ms
        return (
            "# HELP voya_http_requests_total HTTP responses served.\n"
            "# TYPE voya_http_requests_total counter\n"
            f"voya_http_requests_total {requests}\n"
            "# HELP voya_http_errors_total HTTP responses with status 500 or higher.\n"
            "# TYPE voya_http_errors_total counter\n"
            f"voya_http_errors_total {errors}\n"
            "# HELP voya_http_duration_ms_sum Sum of request durations in milliseconds.\n"
            "# TYPE voya_http_duration_ms_sum counter\n"
            f"voya_http_duration_ms_sum {duration}\n"
        )


METRICS = Metrics()
