import json
import shutil
from decimal import Decimal

import pytest

from mordin.data import DATA_DIR, DataFileError, load_amendments, load_limits, load_prices
from mordin.fertilizer.amendments import build_ph_plan, classify_ph

FIXTURES = DATA_DIR.parent / "tests" / "fixtures"


@pytest.fixture
def env():
    return load_amendments(), load_prices(), load_limits()


def _ph(name):
    return json.loads((FIXTURES / f"ph_only_{name}.json").read_text(encoding="utf-8"))["ph"]


def test_classify_boundaries(env):
    table = env[0]
    assert classify_ph(5.99, table) == "acidic"
    assert classify_ph(6.0, table) == "balanced"
    assert classify_ph(6.5, table) == "balanced"
    assert classify_ph(6.51, table) == "alkaline"


def test_acidic_plan(env):
    table, prices, limits = env
    plan = build_ph_plan(_ph("acidic"), 5, table, prices, limits)
    assert plan.source == "ph_only"
    assert plan.ph_class == "acidic"
    assert plan.uses_demo_rules is True
    by_key = {i.key: i for i in plan.items}
    assert set(by_key) == {"agri_lime", "dolomite"}
    lime = by_key["agri_lime"]
    assert lime.rate_kg_per_rai == Decimal(100)
    assert lime.total_kg == Decimal("500.0")
    assert lime.total_price_thb == Decimal(2000)


def test_balanced_gives_no_material(env):
    table, prices, limits = env
    plan = build_ph_plan(_ph("balanced"), 5, table, prices, limits)
    assert plan.ph_class == "balanced"
    assert plan.items == ()


def test_alkaline_class_without_material_gives_no_item(env):
    table, prices, limits = env
    plan = build_ph_plan(_ph("alkaline"), 5, table, prices, limits)
    assert plan.ph_class == "alkaline"
    assert plan.items == ()


def test_totals_scale_with_area(env):
    table, prices, limits = env
    one = build_ph_plan(5.2, 1, table, prices, limits).items[0]
    four = build_ph_plan(5.2, 4, table, prices, limits).items[0]
    assert four.total_kg == one.total_kg * 4
    assert four.rate_kg_per_rai == one.rate_kg_per_rai


@pytest.fixture
def data_dir(tmp_path):
    dest = tmp_path / "data"
    shutil.copytree(DATA_DIR, dest)
    return dest


def test_missing_table_raises(data_dir):
    (data_dir / "soil_amendments.json").unlink()
    with pytest.raises(DataFileError) as e:
        load_amendments(data_dir)
    assert "soil_amendments.json" in e.value.path


def _edit(data_dir, fn):
    p = data_dir / "soil_amendments.json"
    obj = json.loads(p.read_text(encoding="utf-8"))
    fn(obj)
    p.write_text(json.dumps(obj, ensure_ascii=False), encoding="utf-8")


def test_placeholder_without_label_raises(data_dir):
    _edit(data_dir, lambda o: o.update(label=""))
    with pytest.raises(DataFileError):
        load_amendments(data_dir)


def test_rate_above_max_raises(data_dir):
    _edit(data_dir, lambda o: o["materials"]["acidic"][0].update(rate_kg_per_rai=999))
    with pytest.raises(DataFileError) as e:
        load_amendments(data_dir)
    assert "soil_amendments.json" in e.value.path


def test_missing_class_raises(data_dir):
    _edit(data_dir, lambda o: o["materials"].pop("alkaline"))
    with pytest.raises(DataFileError):
        load_amendments(data_dir)
