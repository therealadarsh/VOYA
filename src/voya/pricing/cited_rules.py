"""Overlay demo destination rules with cited `data/` values (M2)."""

from __future__ import annotations

import os
from decimal import Decimal

from voya.catalog import Catalog, Destination
from voya.data.loaders import load_data_bundle

D = Decimal

# Demo catalog destination id → sales_tax jurisdiction key in data/
_JURISDICTION: dict[str, str] = {
    "chicago": "chicago",
    "new-york": "nyc",
    "san-francisco": "sf",
}

# Demo catalog city → primary rail transit key in RuleTable.transit_fares
_TRANSIT_KEY: dict[str, str] = {
    "chicago": "cta:rail:l_train_regular",
    "new-york": "mta:subway:subway_local",
    "san-francisco": "sfmta:bus_rail:muni_single_ride",
}

# Park id → NPS park code in cited fees
_PARK_CODE: dict[str, str] = {
    "yosemite": "YOSE",
    "indiana-dunes": "INDU",
}


def cited_rules_enabled() -> bool:
    return os.environ.get("VOYA_CITED_RULES", "1").strip().lower() not in {
        "0",
        "false",
        "no",
    }


def overlay_rules(cat: Catalog) -> Catalog:
    """Return catalog with cited sales tax, transit and park fees where available."""
    if not cited_rules_enabled():
        return cat
    bundle = load_data_bundle()
    dests: list[Destination] = []
    for dest in cat.destinations:
        rules = dest.rules
        jur = _JURISDICTION.get(dest.id)
        if jur and jur in bundle.rules.sales_tax:
            tax = bundle.rules.sales_tax[jur]
            rules = rules.model_copy(
                update={"sales_tax_pct": (tax.combined_rate * 100).quantize(D("0.01"))}
            )
        tkey = _TRANSIT_KEY.get(dest.id)
        if tkey and tkey in bundle.rules.transit_fares:
            fare = bundle.rules.transit_fares[tkey]
            rules = rules.model_copy(update={"transit_fare": fare.full_fare_usd})
        pcode = _PARK_CODE.get(dest.id)
        if pcode and pcode in bundle.rules.park_fees:
            fee = bundle.rules.park_fees[pcode]
            rules = rules.model_copy(update={"park_fee_vehicle": fee.amount_usd})
        dests.append(dest.model_copy(update={"rules": rules}))
    return cat.model_copy(update={"destinations": tuple(dests)})
