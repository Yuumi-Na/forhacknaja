import json
from pathlib import Path

from mordin.data import load_limits
from mordin.vision.schemas import SheetReading, validate_reading

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"
LIMITS = load_limits()


def _ok() -> SheetReading:
    text = (FIXTURES / "demo_sheet_ok.json").read_text(encoding="utf-8")
    return SheetReading.model_validate(json.loads(text))


def test_valid_reading_is_unchanged():
    r = _ok()
    assert validate_reading(r, LIMITS) == r


def test_out_of_range_numbers_become_unreadable():
    r = _ok().model_copy(update={"ph": 14.0, "p": -1})
    out = validate_reading(r, LIMITS)
    assert out.ph == "unreadable" and out.p == "unreadable"
    assert out.k == 45


def test_unknown_texture_becomes_unreadable():
    r = _ok().model_copy(update={"soil_texture": "หิน"})
    assert validate_reading(r, LIMITS).soil_texture == "unreadable"


def test_json_round_trip_keeps_recommendations():
    r = _ok()
    again = SheetReading.model_validate_json(r.model_dump_json())
    assert again == r
    assert again.sheet_recommendations[0].rate_kg_per_rai == 20.98


def test_loads_limits_by_default():
    r = _ok().model_copy(update={"ph": 99})
    assert validate_reading(r).ph == "unreadable"


# Regression: the model sent sheet_recommendations as a JSON string, so every read failed.
def test_recommendations_as_json_string_are_decoded():
    r = SheetReading.model_validate(
        {
            "ph": "7.1",
            "sheet_recommendations": '[{"fertilizer": "46-0-0", "rate_kg_per_rai": "20.98"},'
            ' {"fertilizer": "18-46-0", "rate_kg_per_rai": 13.04}]',
        }
    )
    assert r.ph == 7.1
    assert [i.fertilizer for i in r.sheet_recommendations] == ["46-0-0", "18-46-0"]
    assert r.sheet_recommendations[0].rate_kg_per_rai == 20.98


def test_recommendations_free_text_is_still_rejected():
    import pytest
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        SheetReading.model_validate({"sheet_recommendations": "46-0-0: 20.98 kg/rai"})


def test_texture_with_leading_din_is_normalized():
    r = _ok().model_copy(update={"soil_texture": "ดินร่วนปนดินเหนียว"})
    assert validate_reading(r, LIMITS).soil_texture == "ร่วนปนดินเหนียว"


def test_texture_din_kept_when_exact_match():
    r = _ok().model_copy(update={"soil_texture": "ดินเหนียว"})
    assert validate_reading(r, LIMITS).soil_texture == "ดินเหนียว"
