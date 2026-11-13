"""Runtime settings. Production refuses to start until required values are set.

Missing hosting, SMTP, or invite-code decisions stay as questions in
`production_problems`. This module does not invent those values.
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

_TRUE = {"1", "true", "yes"}
_FALSE = {"0", "false", "no"}


def _raw(env: Mapping[str, str], key: str) -> str | None:
    value = env.get(key)
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


def _bool(value: str | None, *, default: bool) -> bool:
    if value is None:
        return default
    lowered = value.strip().lower()
    if lowered in _TRUE:
        return True
    if lowered in _FALSE:
        return False
    return default


@dataclass(frozen=True)
class Settings:
    env: str
    invite_code: str | None
    public_url: str
    dev_signin: bool
    data_dir: Path
    smtp_host: str | None
    smtp_port: int
    smtp_username: str | None
    smtp_password: str | None
    smtp_from: str | None
    preview_label: bool
    log_json: bool

    @property
    def production(self) -> bool:
        return self.env == "production"

    @property
    def invite_required(self) -> bool:
        return bool(self.invite_code)


def load_settings(environ: Mapping[str, str] | None = None) -> Settings:
    env = os.environ if environ is None else environ
    name = (_raw(env, "VOYA_ENV") or "development").lower()
    port_raw = _raw(env, "VOYA_SMTP_PORT") or "587"
    try:
        smtp_port = int(port_raw)
    except ValueError:
        smtp_port = 587
    log_default = "json" if name == "production" else "text"
    log_format = (_raw(env, "VOYA_LOG_FORMAT") or log_default).lower()
    return Settings(
        env=name,
        invite_code=_raw(env, "VOYA_INVITE_CODE"),
        public_url=_raw(env, "VOYA_PUBLIC_URL") or "http://localhost:8000",
        dev_signin=_bool(_raw(env, "VOYA_DEV_SIGNIN"), default=True),
        data_dir=Path(_raw(env, "VOYA_DATA_DIR") or "var"),
        smtp_host=_raw(env, "VOYA_SMTP_HOST"),
        smtp_port=smtp_port,
        smtp_username=_raw(env, "VOYA_SMTP_USERNAME"),
        smtp_password=env.get("VOYA_SMTP_PASSWORD"),
        smtp_from=_raw(env, "VOYA_SMTP_FROM"),
        preview_label=_bool(_raw(env, "VOYA_PREVIEW_LABEL"), default=True),
        log_json=log_format == "json",
    )


def production_problems(settings: Settings) -> list[str]:
    """Questions and missing values that block a production start. Empty in development."""
    if not settings.production:
        return []
    problems: list[str] = []
    if settings.invite_code is None or len(settings.invite_code) < 8:
        problems.append(
            "What invite code should the private preview require? "
            "Set VOYA_INVITE_CODE (8 or more characters)."
        )
    if not settings.public_url.startswith("https://"):
        problems.append("What public https URL should magic links use? Set VOYA_PUBLIC_URL.")
    if settings.dev_signin:
        problems.append(
            "Set VOYA_DEV_SIGNIN=0 so production sign-in sends email instead of returning a token."
        )
    if not settings.data_dir.is_absolute():
        problems.append(
            "Which absolute directory should hold the database so it survives redeploys? "
            "Set VOYA_DATA_DIR."
        )
    smtp_ready = all(
        (
            settings.smtp_host,
            settings.smtp_from,
            settings.smtp_username,
            settings.smtp_password,
        )
    )
    if not smtp_ready:
        problems.append(
            "What SMTP host, port, username, password, and From address should magic-link "
            "email use? Set VOYA_SMTP_HOST, VOYA_SMTP_PORT, VOYA_SMTP_USERNAME, "
            "VOYA_SMTP_PASSWORD, and VOYA_SMTP_FROM."
        )
    return problems
