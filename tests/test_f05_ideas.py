"""Idea-bank file rules."""

from __future__ import annotations

import json
from pathlib import Path

from voya.ideas import check_idea_files, check_idea_text

_SAMPLE = Path("data/ideas/nyc.json")


def test_sample_file_is_marked_as_a_sample() -> None:
    raw = json.loads(_SAMPLE.read_text(encoding="utf-8"))
    assert raw["synthetic"] is True
    assert raw["note"] == "Sample; owner replaces with their own picks"
    assert check_idea_files() == []
    for day in raw["days"].values():
        for slot in day.values():
            for option in slot["options"]:
                assert option["curated_by"] == "sample"
                assert "price" not in option


def test_missing_slot_is_rejected() -> None:
    raw = json.loads(_SAMPLE.read_text(encoding="utf-8"))
    del raw["days"]["1"]["morning"]
    problems = check_idea_text(json.dumps(raw), name="nyc.json")
    assert any("missing slot morning" in item for item in problems)


def test_too_few_and_too_many_options_are_rejected() -> None:
    raw = json.loads(_SAMPLE.read_text(encoding="utf-8"))
    options = raw["days"]["1"]["morning"]["options"]
    raw["days"]["1"]["morning"]["options"] = options[:1]
    few = check_idea_text(json.dumps(raw), name="nyc.json")
    assert any("1 options" in item for item in few)
    raw["days"]["1"]["morning"]["options"] = options * 3
    many = check_idea_text(json.dumps(raw), name="nyc.json")
    assert any("need 2 to 6" in item for item in many)


def test_duplicate_ids_are_rejected() -> None:
    raw = json.loads(_SAMPLE.read_text(encoding="utf-8"))
    raw["days"]["1"]["afternoon"]["options"][0]["id"] = raw["days"]["1"]["morning"]["options"][0][
        "id"
    ]
    problems = check_idea_text(json.dumps(raw), name="nyc.json")
    assert any("duplicate id" in item for item in problems)


def test_price_like_field_is_rejected() -> None:
    raw = json.loads(_SAMPLE.read_text(encoding="utf-8"))
    raw["days"]["1"]["morning"]["options"][0]["price"] = "0"
    problems = check_idea_text(json.dumps(raw), name="nyc.json")
    assert any("price-like field price" in item for item in problems)


def test_coordinates_over_3_decimals_are_rejected() -> None:
    raw = json.loads(_SAMPLE.read_text(encoding="utf-8"))
    raw["days"]["1"]["morning"]["options"][0]["lat"] = 40.71281
    raw["days"]["1"]["morning"]["options"][0]["lng"] = -74.0134
    problems = check_idea_text(json.dumps(raw), name="nyc.json")
    assert any("40.71281" in item and "decimals" in item for item in problems)
    assert any("-74.0134" in item or "74.0134" in item for item in problems)
