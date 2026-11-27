"""Per-slot first-week ideas. One option is chosen per slot, seeded by the plan.

The file holds no prices. A cost is attached only when a pick maps to a cited
place. Until then the plan view says the price is not yet checked.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

_ROOT = Path(__file__).resolve().parents[2]
_IDEAS_DIR = _ROOT / "data" / "ideas"
_NYC_FARE = _ROOT / "data" / "cities" / "nyc" / "transit_fares.json"
_SLOTS = ("morning", "afternoon", "evening")
_AREA_FOR = {"new-york": "nyc", "nyc": "nyc"}
_PRICE_KEYS = {
    "admission",
    "amount",
    "amounts",
    "close",
    "cost",
    "costs",
    "fare",
    "fares",
    "fee",
    "fees",
    "hour",
    "hours",
    "open",
    "price",
    "prices",
    "rating",
    "reviews",
    "statistic",
    "statistics",
    "tax",
    "toll",
    "usd",
}
_COORD_KEYS = {"lat", "lng", "latitude", "longitude"}
_CURATORS = {"sample", "owner"}


@dataclass(frozen=True)
class IdeaOption:
    id: str
    title: str
    place_ref: str | None
    tags: tuple[str, ...]
    indoor: bool
    duration_min: int
    why: str
    curated_by: str

    def place_key(self) -> str:
        return self.place_ref or self.title


@dataclass(frozen=True)
class IdeaBank:
    synthetic: bool
    source: str
    observed_at: str
    quote: str
    area: str
    note: str
    days: dict[int, dict[str, tuple[IdeaOption, ...]]]

    def option(self, option_id: str) -> IdeaOption:
        for day in self.days.values():
            for options in day.values():
                for item in options:
                    if item.id == option_id:
                        return item
        raise KeyError(option_id)

    def slot(self, day: int, name: str) -> tuple[IdeaOption, ...]:
        return self.days[day][name]


def nyc_transit() -> dict[str, Any] | None:
    """The cited subway fare, or None when that file is missing a fare."""
    if not _NYC_FARE.is_file():
        return None
    raw = json.loads(_NYC_FARE.read_text(encoding="utf-8"))
    fares = raw.get("fares") or []
    if not fares:
        return None
    fare = fares[0]
    return {
        "label": fare["label"],
        "amount": fare["full_fare_usd"],
        "source": raw["source"],
        "url": raw.get("url"),
        "observed_at": raw["observed_at"],
        "quote": raw["quote"],
        "is_estimate": True,
    }


def _unwrap(node: Any) -> Any:
    if isinstance(node, tuple) and node and node[0] == "n":
        token = str(node[1])
        if any(mark in token.lower() for mark in (".", "e")):
            return float(token)
        return int(token)
    if isinstance(node, dict):
        return {str(key): _unwrap(value) for key, value in node.items()}
    if isinstance(node, list):
        return [_unwrap(item) for item in node]
    return node


def _walk_shape(node: Any, path: str, problems: list[str]) -> None:
    if isinstance(node, dict):
        for key, value in node.items():
            name = str(key)
            here = f"{path}.{name}"
            if name.lower() in _PRICE_KEYS:
                problems.append(f"{path}: price-like field {name}")
            if isinstance(value, tuple) and value and value[0] == "n":
                token = str(value[1])
                if name.lower() in _COORD_KEYS and "." in token:
                    places = len(token.split(".", 1)[1])
                    if places > 3:
                        problems.append(f"{here}: {token} has {places} decimals (max 3)")
            else:
                _walk_shape(value, here, problems)
    elif isinstance(node, list):
        for index, item in enumerate(node):
            _walk_shape(item, f"{path}[{index}]", problems)


def _one_sentence(text: str) -> bool:
    stripped = text.strip()
    if not stripped or "\n" in stripped:
        return False
    if ". " in stripped:
        return False
    return stripped.endswith((".", "!", "?"))


def _option_problems(raw: Any, path: str) -> list[str]:
    if not isinstance(raw, dict):
        return [f"{path}: option must be an object"]
    problems: list[str] = []
    required = ("id", "title", "place_ref", "tags", "indoor", "duration_min", "why", "curated_by")
    for field in required:
        if field not in raw:
            problems.append(f"{path}: missing {field}")
    if problems:
        return problems
    if not isinstance(raw["id"], str) or not raw["id"].strip():
        problems.append(f"{path}: id must be a non-empty string")
    if not isinstance(raw["title"], str) or not raw["title"].strip():
        problems.append(f"{path}: title must be a non-empty string")
    if raw["place_ref"] is not None and (
        not isinstance(raw["place_ref"], str) or not raw["place_ref"].strip()
    ):
        problems.append(f"{path}: place_ref must be a string or null")
    if not isinstance(raw["tags"], list) or not all(isinstance(tag, str) for tag in raw["tags"]):
        problems.append(f"{path}: tags must be a list of strings")
    if not isinstance(raw["indoor"], bool):
        problems.append(f"{path}: indoor must be true or false")
    if type(raw["duration_min"]) is not int or raw["duration_min"] < 1:
        problems.append(f"{path}: duration_min must be a positive integer")
    if not isinstance(raw["why"], str) or not _one_sentence(raw["why"]):
        problems.append(f"{path}: why must be one sentence")
    if raw["curated_by"] not in _CURATORS:
        problems.append(f"{path}: curated_by must be sample or owner")
    return problems


def check_idea_text(text: str, *, name: str = "ideas.json") -> list[str]:
    """Return one problem per broken rule. An empty list means the file is usable."""
    try:
        raw_tree = json.loads(
            text, parse_int=lambda token: ("n", token), parse_float=lambda token: ("n", token)
        )
    except json.JSONDecodeError as exc:
        return [f"{name}: {exc.msg}"]
    problems: list[str] = []
    _walk_shape(raw_tree, name, problems)
    data = _unwrap(raw_tree)
    if not isinstance(data, dict):
        return problems + [f"{name}: file must be an object"]
    for field in ("synthetic", "source", "observed_at", "quote", "area", "days"):
        if field not in data:
            problems.append(f"{name}: missing {field}")
    if not isinstance(data.get("synthetic"), bool):
        problems.append(f"{name}: synthetic must be true or false")
    elif data["synthetic"] is True and not str(data.get("note") or "").strip():
        problems.append(f"{name}: synthetic file needs a note")
    days = data.get("days")
    if not isinstance(days, dict):
        return problems + [f"{name}: days must be an object"]
    expected = {str(number) for number in range(1, 8)}
    if set(days) != expected:
        problems.append(f"{name}: days must be 1 through 7")
    seen: dict[str, str] = {}
    for day_key in sorted(expected & set(days), key=int):
        day = days[day_key]
        day_path = f"{name} day {day_key}"
        if not isinstance(day, dict):
            problems.append(f"{day_path}: must be an object")
            continue
        if set(day) != set(_SLOTS):
            missing = [slot for slot in _SLOTS if slot not in day]
            if missing:
                problems.append(f"{day_path}: missing slot {missing[0]}")
            extra = sorted(set(day) - set(_SLOTS))
            if extra:
                problems.append(f"{day_path}: unknown slot {extra[0]}")
        for slot in _SLOTS:
            if slot not in day:
                continue
            slot_path = f"{day_path} {slot}"
            body = day[slot]
            options = body.get("options") if isinstance(body, dict) else None
            if not isinstance(options, list):
                problems.append(f"{slot_path}: options must be a list")
                continue
            count = len(options)
            if count < 2 or count > 6:
                problems.append(f"{slot_path}: {count} options (need 2 to 6)")
            for index, option in enumerate(options):
                option_path = f"{slot_path} option {index + 1}"
                problems.extend(_option_problems(option, option_path))
                if isinstance(option, dict) and isinstance(option.get("id"), str):
                    option_id = option["id"]
                    if option_id in seen:
                        problems.append(f"{name}: duplicate id {option_id}")
                    else:
                        seen[option_id] = option_path
    return problems


def _bank_from_text(text: str, *, name: str) -> IdeaBank:
    problems = check_idea_text(text, name=name)
    if problems:
        raise ValueError("\n".join(problems))
    data = json.loads(text)
    days: dict[int, dict[str, tuple[IdeaOption, ...]]] = {}
    for day_key, day in data["days"].items():
        slots: dict[str, tuple[IdeaOption, ...]] = {}
        for slot in _SLOTS:
            built: list[IdeaOption] = []
            for option in day[slot]["options"]:
                built.append(
                    IdeaOption(
                        id=option["id"],
                        title=option["title"],
                        place_ref=option["place_ref"],
                        tags=tuple(option["tags"]),
                        indoor=bool(option["indoor"]),
                        duration_min=int(option["duration_min"]),
                        why=option["why"],
                        curated_by=option["curated_by"],
                    )
                )
            slots[slot] = tuple(built)
        days[int(day_key)] = slots
    return IdeaBank(
        synthetic=bool(data["synthetic"]),
        source=str(data["source"]),
        observed_at=str(data["observed_at"]),
        quote=str(data["quote"]),
        area=str(data["area"]),
        note=str(data.get("note") or ""),
        days=days,
    )


@lru_cache(maxsize=8)
def load_area(area: str) -> IdeaBank | None:
    path = _IDEAS_DIR / f"{area}.json"
    if not path.is_file():
        return None
    return _bank_from_text(path.read_text(encoding="utf-8"), name=str(path.relative_to(_ROOT)))


def check_idea_files(root: Path | None = None) -> list[str]:
    base = (root or _ROOT) / "data" / "ideas"
    if not base.is_dir():
        return []
    problems: list[str] = []
    files = sorted(base.glob("*.json"))
    for path in files:
        problems.extend(check_idea_text(path.read_text(encoding="utf-8"), name=str(path.name)))
    return problems


def choose(bank: IdeaBank, seed: str, days: int) -> tuple[dict[str, dict[str, str]], list[str]]:
    """Pick one unused option per slot. The same seed always returns the same picks."""
    count = min(max(days, 1), 7)
    used: set[str] = set()
    picks: dict[str, dict[str, str]] = {}
    chosen: list[str] = []
    for day in range(1, count + 1):
        picks[str(day)] = {}
        for slot in _SLOTS:
            ordered = sorted(
                bank.slot(day, slot),
                key=lambda option: hashlib.sha256(
                    f"{seed}|{day}|{slot}|{option.id}".encode()
                ).hexdigest(),
            )
            picked = next((option for option in ordered if option.place_key() not in used), None)
            if picked is None:
                raise ValueError(f"day {day} {slot} has no unused option")
            used.add(picked.place_key())
            picks[str(day)][slot] = picked.id
            chosen.append(picked.id)
    return picks, chosen


def initial_ideas(plan_id: str, request_json: str) -> tuple[str, list[str]]:
    try:
        request = json.loads(request_json)
    except json.JSONDecodeError:
        return "null", []
    if not isinstance(request, dict):
        return "null", []
    area = _AREA_FOR.get(str(request.get("destination") or ""))
    if not area:
        return "null", []
    bank = load_area(area)
    if bank is None:
        return "null", []
    try:
        day_count = int(request.get("days") or 1)
    except (TypeError, ValueError):
        day_count = 1
    picks, chosen = choose(bank, plan_id, day_count)
    payload = {"area": area, "picks": picks}
    return json.dumps(payload, sort_keys=True), chosen


def _stored(ideas_json: str | None) -> dict[str, Any] | None:
    if not ideas_json or ideas_json == "null":
        return None
    raw = json.loads(ideas_json)
    if not isinstance(raw, dict) or "picks" not in raw:
        return None
    return raw


def option_ids(ideas_json: str | None) -> list[str]:
    stored = _stored(ideas_json)
    if stored is None:
        return []
    found: list[str] = []
    picks = stored.get("picks")
    if not isinstance(picks, dict):
        return []
    for day in picks.values():
        if isinstance(day, dict):
            for option_id in day.values():
                if isinstance(option_id, str):
                    found.append(option_id)
    return found


def rotate(ideas_json: str, day: int, slot: str) -> tuple[str, str, str]:
    """Move one slot to the next unused option. Returns new JSON, left id, new id."""
    stored = _stored(ideas_json)
    if stored is None:
        raise ValueError("This plan has no classic picks.")
    if slot not in _SLOTS or str(day) not in stored["picks"]:
        raise ValueError("That slot is not on this plan.")
    bank = load_area(str(stored["area"]))
    if bank is None:
        raise ValueError("That idea file is missing.")
    current_id = str(stored["picks"][str(day)][slot])
    options = list(bank.slot(day, slot))
    ids = [option.id for option in options]
    if current_id not in ids:
        raise ValueError("The saved pick is not in the idea file.")
    used: set[str] = set()
    for day_key, slots in stored["picks"].items():
        for slot_name, option_id in slots.items():
            if day_key == str(day) and slot_name == slot:
                continue
            used.add(bank.option(str(option_id)).place_key())
    start = ids.index(current_id)
    arrived = current_id
    for step in range(1, len(ids) + 1):
        candidate = options[(start + step) % len(ids)]
        if candidate.place_key() in used:
            continue
        arrived = candidate.id
        break
    stored["picks"][str(day)][slot] = arrived
    return json.dumps(stored, sort_keys=True), current_id, arrived


def public_view(ideas_json: str | None) -> dict[str, Any] | None:
    stored = _stored(ideas_json)
    if stored is None:
        return None
    bank = load_area(str(stored["area"]))
    if bank is None:
        return None
    days: list[dict[str, Any]] = []
    for day_key in sorted(stored["picks"], key=int):
        slots_out: list[dict[str, Any]] = []
        for slot in _SLOTS:
            option_id = stored["picks"][day_key].get(slot)
            if not isinstance(option_id, str):
                continue
            option = bank.option(option_id)
            slots_out.append(
                {
                    "slot": slot,
                    "id": option.id,
                    "title": option.title,
                    "why": option.why,
                    "indoor": option.indoor,
                    "duration_min": option.duration_min,
                    "place_ref": option.place_ref,
                    "curated_by": option.curated_by,
                    "price_label": "price not yet checked",
                }
            )
        days.append({"day": int(day_key), "slots": slots_out})
    return {
        "label": "Classic picks",
        "area": stored["area"],
        "note": bank.note,
        "days": days,
    }


def day_one_titles(seed: str) -> tuple[str, str, str]:
    bank = load_area("nyc")
    if bank is None:
        raise ValueError("NYC ideas are missing")
    picks, _chosen = choose(bank, seed, 1)
    titles = []
    for slot in _SLOTS:
        titles.append(bank.option(picks["1"][slot]).title)
    return (titles[0], titles[1], titles[2])
