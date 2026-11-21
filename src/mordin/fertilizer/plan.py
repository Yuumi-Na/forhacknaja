"""Shared result types for every path (sheet, basic formula, pH only). No network."""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Literal


@dataclass(frozen=True)
class PlanItem:
    key: str  # "urea", "15-15-15", "agri_lime"
    rate_kg_per_rai: Decimal
    total_kg: Decimal
    total_price_thb: Decimal | None  # None -> "ไม่มีราคา"
    script_kg: int
    rate_small_bags_per_rai: Decimal


@dataclass(frozen=True)
class Plan:
    source: Literal["sheet", "basic_formula", "ph_only"]
    area_rai: Decimal
    items: tuple[PlanItem, ...]
    price_date: str
    uses_demo_rules: bool  # True for basic_formula and ph_only
    ph_class: str | None = None
    soil_status: dict[str, str] = field(default_factory=dict)
