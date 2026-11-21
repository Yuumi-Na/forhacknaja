"""Per-item totals from a per-rai rate and area_rai. Pure code, no network."""

from __future__ import annotations

from decimal import Decimal
from typing import Any, Mapping

from .plan import PlanItem
from .rounding import round_half_up, to_decimal


def unrounded_total_kg(rate_kg_per_rai: Any, area_rai: Any) -> Decimal:
    """rate x area with no rounding."""
    return to_decimal(rate_kg_per_rai) * to_decimal(area_rai)


def compute_item(
    rate: Any,
    area_rai: Any,
    price_per_kg: Any,
    limits: Mapping[str, Any],
    *,
    key: str = "",
) -> PlanItem:
    """Build one PlanItem. The rate is kept exactly as given.

    total_kg: 0.1 kg half-up. total_price_thb: whole baht half-up, or None when
    there is no price. script_kg: whole kg half-up. rate_small_bags_per_rai:
    rate / small_bag_kg to the nearest half bag (0.25 rounds up to 0.5).
    All derived values start from the unrounded total.
    """
    rate_d = to_decimal(rate)
    total = unrounded_total_kg(rate_d, area_rai)
    price = None if price_per_kg is None else round_half_up(total * to_decimal(price_per_kg), 0)
    bag_kg = to_decimal(limits["small_bag_kg"])
    bags = round_half_up(rate_d / bag_kg * 2, 0) / 2
    return PlanItem(
        key=key,
        rate_kg_per_rai=rate_d,
        total_kg=round_half_up(total, 1),
        total_price_thb=price,
        script_kg=int(round_half_up(total, 0)),
        rate_small_bags_per_rai=bags,
    )
