"""Feature flags for future paid tiers (MVP: everything free)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Entitlements:
    saved_trips: bool = True
    live_tracking: bool = True
    ai_helper: bool = True
    max_plans_per_day: int = 50


def for_owner(_owner: str | None) -> Entitlements:
    return Entitlements()
