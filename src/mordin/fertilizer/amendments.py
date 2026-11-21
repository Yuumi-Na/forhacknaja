"""pH-only soil improvement: pH class, material and totals. Pure code, no network."""

from __future__ import annotations

from typing import Any, Mapping

from .plan import Plan
from .rounding import to_decimal
from .totals import compute_item


def classify_ph(ph: Any, table: Mapping[str, Any]) -> str:
    """acidic below acidic_below, alkaline above alkaline_above, else balanced."""
    value = to_decimal(ph)
    limits = table["ph_limits"]
    if value < to_decimal(limits["acidic_below"]):
        return "acidic"
    if value > to_decimal(limits["alkaline_above"]):
        return "alkaline"
    return "balanced"


def build_ph_plan(
    ph: Any,
    area_rai: Any,
    table: Mapping[str, Any],
    prices: Mapping[str, Any],
    limits: Mapping[str, Any],
) -> Plan:
    """One PlanItem per material of the pH class. No material gives no items.

    The rate is capped at max_rate_kg_per_rai.
    """
    ph_class = classify_ph(ph, table)
    per_kg = prices.get("prices_per_kg", {})
    items = []
    for row in table["materials"].get(ph_class, []):
        rate = min(to_decimal(row["rate_kg_per_rai"]), to_decimal(row["max_rate_kg_per_rai"]))
        items.append(compute_item(rate, area_rai, per_kg.get(row["key"]), limits, key=row["key"]))
    return Plan(
        source="ph_only",
        area_rai=to_decimal(area_rai),
        items=tuple(items),
        price_date=str(prices.get("date", "")),
        uses_demo_rules=True,
        ph_class=ph_class,
    )
