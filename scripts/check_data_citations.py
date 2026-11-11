"""Ensure every non-synthetic file under data/ has source, observed_at, quote."""

from __future__ import annotations

import sys

from voya.pricing.rules import assert_all_cited


def main() -> int:
    n = assert_all_cited()
    print(f"check_data_citations: {n} cited file(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
