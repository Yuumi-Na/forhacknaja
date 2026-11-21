import json
from pathlib import Path

import pytest

from mordin.data import load_basic_formula
from mordin.fertilizer.formula import soil_status

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"


@pytest.fixture(scope="module")
def rules():
    return load_basic_formula()


def fixture(name):
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def test_low_k_sheet(rules):
    s = soil_status(fixture("demo_sheet_low_k.json"), rules)
    assert s == {
        "om": "fair", "p": "fair", "k": "low", "ca": "fair",
        "mg": "fair", "ph": "good", "soil_texture": "good",
    }


def test_high_p_sheet(rules):
    s = soil_status(fixture("demo_sheet_high_p.json"), rules)
    assert s["p"] == "good" and s["k"] == "fair" and s["om"] == "fair"


def test_acidic_sheet(rules):
    s = soil_status(fixture("demo_sheet_acidic.json"), rules)
    assert s["ph"] == "needs_action"
    assert s["om"] == "needs_action"
    assert s["soil_texture"] == "needs_action"


def test_unreadable_and_none_values_are_skipped(rules):
    s = soil_status(fixture("demo_sheet_partial.json"), rules)
    assert set(s) == {"om", "k", "ca", "ph", "soil_texture"}
    assert soil_status({"om": None, "ph": None, "soil_texture": None}, rules) == {}
    assert soil_status(fixture("demo_not_dld.json"), rules) == {}


def test_band_boundaries_use_lower_edge(rules):
    assert soil_status({"k": 60}, rules)["k"] == "fair"
    assert soil_status({"k": 59.9}, rules)["k"] == "low"
    assert soil_status({"ph": 6.0}, rules)["ph"] == "good"
    assert soil_status({"ph": 7.5}, rules)["ph"] == "fair"


def test_statuses_are_from_the_four_categories(rules):
    for name in FIXTURES.glob("demo_sheet_*.json"):
        for v in soil_status(json.loads(name.read_text(encoding="utf-8")), rules).values():
            assert v in {"good", "fair", "low", "needs_action"}


def test_unknown_texture_gets_no_status(rules):
    assert soil_status({"soil_texture": "หิน"}, rules) == {}
