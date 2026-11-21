from decimal import Decimal

from mordin.fertilizer.sheet_plan import build_sheet_plan
from mordin.fertilizer.totals import compute_item, unrounded_total_kg

LIMITS = {"small_bag_kg": 5}
PRICES = {"date": "2025-01-01", "prices_per_kg": {"urea": 20.0, "16-16-8": None}}


def test_script_kg_rounds_to_whole_kg():
    assert compute_item("20.98", 5, 20, LIMITS).script_kg == 105
    assert compute_item("20.98", 5, 20, LIMITS).total_kg == Decimal("104.9")
    assert compute_item(12, 5, 20, LIMITS).script_kg == 60


def test_small_bags_nearest_half():
    assert compute_item("20.98", 1, 20, LIMITS).rate_small_bags_per_rai == Decimal("4")
    assert compute_item(12, 1, 20, LIMITS).rate_small_bags_per_rai == Decimal("2.5")
    assert compute_item(1, 1, 20, LIMITS).rate_small_bags_per_rai == Decimal("0")
    # 1.25 kg = 0.25 bag rounds up to half a bag
    assert compute_item("1.25", 1, 20, LIMITS).rate_small_bags_per_rai == Decimal("0.5")


def test_price_whole_baht_and_none_without_price():
    assert compute_item("20.98", 5, 20, LIMITS).total_price_thb == Decimal("2098")
    assert compute_item(10, 2, None, LIMITS).total_price_thb is None


def test_sheet_plan_passes_rate_and_handles_missing_price():
    recs = [
        {"fertilizer": "urea", "rate_kg_per_rai": "20.98"},
        {"fertilizer": "16-16-8", "rate_kg_per_rai": 30},
        {"fertilizer": "99-9-9", "rate_kg_per_rai": 10},
    ]
    plan = build_sheet_plan(recs, 5, PRICES, LIMITS)
    assert plan.source == "sheet" and not plan.uses_demo_rules
    assert [i.key for i in plan.items] == ["urea", "16-16-8", "99-9-9"]
    assert plan.items[0].rate_kg_per_rai == Decimal("20.98")
    assert plan.items[1].total_price_thb is None
    assert plan.items[2].total_price_thb is None
    assert plan.price_date == "2025-01-01"


def test_doubling_area_doubles_unrounded_total():
    rate = Decimal("20.98")
    assert unrounded_total_kg(rate, Decimal("7.3333")) * 2 == unrounded_total_kg(
        rate, Decimal("14.6666")
    )
