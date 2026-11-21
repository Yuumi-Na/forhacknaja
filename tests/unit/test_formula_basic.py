import json
from decimal import Decimal
from itertools import product
from pathlib import Path

import pytest

from mordin.data import load_basic_formula, load_limits
from mordin.fertilizer.formula import FormulaError, calculate_basic

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"


@pytest.fixture(scope="module")
def rules():
    return load_basic_formula()


@pytest.fixture(scope="module")
def limits():
    return load_limits()


def fixture(name):
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def D(s):
    return Decimal(s)


def test_full_values_with_ph(rules):
    r = calculate_basic(fixture("manual_full_ph.json"), rules)
    assert r.amounts_kg_per_rai == {"urea": D(24), "dap": D(17), "mop": D(17)}
    assert r.supplied_kg_per_rai == {"n": D("14.1"), "p2o5": D("7.8"), "k2o": D("10.2")}
    assert r.label == rules["label"]


def test_full_values_without_ph(rules):
    r = calculate_basic(fixture("manual_full_no_ph.json"), rules)
    assert r.amounts_kg_per_rai == {"urea": D(18), "dap": D(9), "mop": D(10)}
    assert r.supplied_kg_per_rai == {"n": D("9.9"), "p2o5": D("4.1"), "k2o": D("6.0")}


def test_missing_fields_raise_naming_the_field(rules):
    with pytest.raises(FormulaError) as e:
        calculate_basic(fixture("manual_missing_fields.json"), rules)
    assert e.value.field == "ca"
    with pytest.raises(FormulaError):
        calculate_basic(fixture("manual_ph_only.json"), rules)


def test_out_of_range_value_names_the_field(rules, limits):
    v = {**fixture("manual_full_no_ph.json"), "k": 5000}
    with pytest.raises(FormulaError) as e:
        calculate_basic(v, rules, limits)
    assert e.value.field == "k"


def test_same_input_same_output(rules):
    v = fixture("manual_full_ph.json")
    assert calculate_basic(v, rules) == calculate_basic(dict(v), rules)


GRID = list(product([0, 1.4, 1.5, 3.4, 3.5, 20], [0, 9.9, 10, 24.9, 25, 39.9, 40, 500], [0, 59.9, 60, 119.9, 120, 1000]))


@pytest.mark.parametrize("om,p,k", GRID)
def test_amounts_within_zero_and_max(rules, om, p, k):
    r = calculate_basic({"om": om, "p": p, "k": k, "ca": 500, "mg": 70}, rules)
    for key, kg in r.amounts_kg_per_rai.items():
        assert 0 <= kg <= rules["max_kg_per_rai"][key]
        assert kg == kg.to_integral_value()


def test_p_at_or_above_sufficient_gives_zero_dap(rules):
    for p in (rules["p_sufficient"], rules["p_sufficient"] + 1, 500):
        r = calculate_basic({"om": 1, "p": p, "k": 50, "ca": 1, "mg": 1}, rules)
        assert r.amounts_kg_per_rai["dap"] == 0
        assert r.supplied_kg_per_rai["p2o5"] == 0


def test_higher_p_never_raises_dap(rules):
    base = {"om": 1, "k": 50, "ca": 500, "mg": 70}
    low = calculate_basic({**base, "p": 8}, rules)
    high = calculate_basic({**base, "p": 30}, rules)
    assert high.amounts_kg_per_rai["dap"] <= low.amounts_kg_per_rai["dap"]
    ps = [0, 5, 9.9, 10, 20, 24.9, 25, 39.9, 40, 100]
    daps = [calculate_basic({**base, "p": p}, rules).amounts_kg_per_rai["dap"] for p in ps]
    assert daps == sorted(daps, reverse=True)


def test_clamp_to_max(rules):
    tight = {**rules, "max_kg_per_rai": {"urea": 5, "dap": 5, "mop": 5}}
    r = calculate_basic({"om": 1, "p": 8, "k": 45, "ca": 1, "mg": 1}, tight)
    assert r.amounts_kg_per_rai == {"urea": D(5), "dap": D(5), "mop": D(5)}
