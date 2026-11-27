"""Client address for rate limits and spend scopes.

`VOYA_TRUSTED_PROXY_IPS` empty means the direct peer is the client.
`X-Forwarded-For` is read only when that peer is in the list, and the address
used is the right-most hop that is not itself a trusted proxy.
"""

from __future__ import annotations


def parse_trusted_proxies(raw: str | None) -> frozenset[str]:
    if not raw:
        return frozenset()
    return frozenset(part.strip() for part in raw.split(",") if part.strip())


def client_address(*, peer: str | None, forwarded_for: str | None, trusted: frozenset[str]) -> str:
    direct = (peer or "").strip() or "anon"
    if not trusted or direct not in trusted:
        return direct
    hops = [part.strip() for part in (forwarded_for or "").split(",") if part.strip()]
    for hop in reversed(hops):
        if hop not in trusted:
            return hop
    return direct
