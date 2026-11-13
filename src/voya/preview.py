"""Invite-code gate for the private preview."""

from __future__ import annotations

import hmac
from hashlib import sha256

COOKIE = "voya_preview"
_EXEMPT = {
    "/healthz",
    "/readyz",
    "/privacy",
    "/terms",
    "/v1/preview/unlock",
    "/v1/auth/verify",
}


def cookie_for(code: str) -> str:
    return hmac.new(code.encode(), b"voya-preview-v1", sha256).hexdigest()


def code_matches(expected: str, provided: str) -> bool:
    if not expected or not provided:
        return False
    return hmac.compare_digest(cookie_for(expected), cookie_for(provided))


def cookie_matches(expected: str | None, cookie: str | None) -> bool:
    if not expected:
        return True
    if not cookie:
        return False
    return hmac.compare_digest(cookie_for(expected), cookie)


def is_exempt(path: str) -> bool:
    if path in _EXEMPT:
        return True
    return path.startswith("/static/")
