"""VOYA CLI: price-check task list and submissions."""

from __future__ import annotations

import argparse
import secrets
import sys
from datetime import UTC, datetime
from decimal import Decimal

from voya.curate.price_check import PriceCheckEntry, approve_price_check, load_pending, submit_price_check

LAUNCH_CHECKS = [
    ("Chicago", "Art Institute of Illinois", "adult admission"),
    ("Chicago", "CTA", "single ride (confirm)"),
    ("New York City", "Metropolitan Museum", "suggested admission"),
    ("San Francisco", "SFMOMA", "adult admission"),
]


def cmd_list(city: str | None) -> int:
    print("# Price-check task list (launch cities)")
    for c, place, item in LAUNCH_CHECKS:
        if city and c.lower() != city.lower():
            continue
        print(f"- [{c}] {place}: {item}")
    pending = load_pending(city)
    if pending:
        print("\n# Pending submissions")
        for p in pending:
            print(f"  {p.id}: {p.place_name} {p.item} est. ${p.amount} ({p.method})")
    return 0


def cmd_submit(
    city: str, place: str, item: str, amount: str, method: str, url: str | None, note: str | None
) -> int:
    entry = PriceCheckEntry(
        id=f"pc_{secrets.token_hex(4)}",
        place_name=place,
        city=city,
        item=item,
        amount=Decimal(amount),
        method=method,  # type: ignore[arg-type]
        source_url=url,
        note=note,
        observed_at=datetime.now(tz=UTC),
        status="pending",
    )
    submit_price_check(entry)
    print(entry.id)
    return 0


def cmd_approve(entry_id: str) -> int:
    if not approve_price_check(entry_id):
        print("not found or already approved", file=sys.stderr)
        return 1
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="voya")
    sub = p.add_subparsers(dest="cmd", required=True)

    pc = sub.add_parser("price-check", help="Price-check workflows")
    pc_sub = pc.add_subparsers(dest="pc_cmd", required=True)

    lst = pc_sub.add_parser("list")
    lst.add_argument("--city")
    lst.set_defaults(run="list")

    subm = pc_sub.add_parser("submit")
    subm.add_argument("--city", required=True)
    subm.add_argument("--place", required=True)
    subm.add_argument("--item", required=True)
    subm.add_argument("--amount", required=True)
    subm.add_argument("--method", default="official_page")
    subm.add_argument("--url")
    subm.add_argument("--note")
    subm.set_defaults(run="submit")

    appr = pc_sub.add_parser("approve")
    appr.add_argument("id")
    appr.set_defaults(run="approve")

    args = p.parse_args(argv)
    if args.cmd != "price-check":
        return 1
    if args.pc_cmd == "list":
        return cmd_list(args.city)
    if args.pc_cmd == "submit":
        return cmd_submit(
            args.city, args.place, args.item, args.amount, args.method, args.url, args.note
        )
    if args.pc_cmd == "approve":
        return cmd_approve(args.id)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
