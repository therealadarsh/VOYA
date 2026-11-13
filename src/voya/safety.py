"""HTTP safety headers and a same-host check for browser POSTs."""

from __future__ import annotations

from urllib.parse import urlparse

_CSP = (
    "default-src 'self'; script-src 'self'; style-src 'self'; "
    "img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; "
    "base-uri 'self'; form-action 'self'"
)


def security_headers(*, production: bool) -> dict[str, str]:
    headers = {
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY",
        "Referrer-Policy": "no-referrer",
        "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
        "Content-Security-Policy": _CSP,
    }
    if production:
        headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains"
    return headers


def origin_allowed(origin: str | None, request_host: str) -> bool:
    """Allow missing Origin (non-browser clients) and same-host browser POSTs."""
    if not origin:
        return True
    parsed = urlparse(origin)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return False
    return parsed.netloc == request_host
