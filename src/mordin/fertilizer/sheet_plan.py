"""Plan for a lab sheet: the sheet's own rates times area_rai. No Demo_Rules."""

from __future__ import annotations

from typing import Any, Iterable, Mapping

from .plan import Plan
from .rounding import to_decimal
from .totals import compute_item


def _get(rec: Any, name: str) -> Any:
    return rec[name] if isinstance(rec, Mapping) else getattr(rec, name)


def build_sheet_plan(
    recs: Iterable[Any],
    area: Any,
    prices: Mapping[str, Any],
    limits: Mapping[str, Any],
) -> Plan:
    """One PlanItem per confirmed recommendation; each rate passes through unchanged.

    `recs` items have `fertilizer` and `rate_kg_per_rai` (objects or dicts).
    `prices` is the loaded fertilizer_prices.json object. A grade missing from
    it, or with a null price, gets total_price_thb None.
    """
    per_kg = prices.get("prices_per_kg", {})
    items = tuple(
        compute_item(
            _get(r, "rate_kg_per_rai"),
            area,
            per_kg.get(_get(r, "fertilizer")),
            limits,
            key=_get(r, "fertilizer"),
        )
        for r in recs
    )
    return Plan(
        source="sheet",
        area_rai=to_decimal(area),
        items=items,
        price_date=str(prices.get("date", "")),
        uses_demo_rules=False,
    )
