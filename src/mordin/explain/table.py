"""Summary table built in code from a Plan. All text is formatted from Decimal values.

The only arithmetic is the sum of the already-rounded item prices that exist.
Descriptions come from `messages.item_description`, never from a model.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from mordin.explain import messages
from mordin.fertilizer.plan import Plan

COLUMNS: tuple[str, ...] = (
    "ชื่อปุ๋ย/วัสดุ",
    "กก./ไร่",
    "รวม (กก.)",
    f"{messages.ESTIMATED_LABEL} ({messages.CURRENCY})",
    "คำอธิบายสั้น",
)
TOTAL_LABEL = "ราคารวม"
PARTIAL_NOTE = "รวมเฉพาะรายการที่มีราคา"


@dataclass(frozen=True)
class SummaryTable:
    heading: str
    columns: tuple[str, ...]
    rows: tuple[tuple[str, ...], ...]
    total_row: tuple[str, ...]
    text_version: str


def _fmt(value: Decimal) -> str:
    """Plain fixed-point text with the Decimal's own decimal places."""
    return format(value, "f")


def build_table(plan: Plan) -> SummaryTable:
    heading = f"แผนสำหรับ {_fmt(plan.area_rai)} ไร่"
    rows: list[tuple[str, ...]] = []
    priced: list[Decimal] = []
    for item in plan.items:
        if item.total_price_thb is None:
            price = messages.NO_PRICE
        else:
            price = f"{_fmt(item.total_price_thb)} {messages.CURRENCY}"
            priced.append(item.total_price_thb)
        rows.append(
            (
                messages.item_name(item.key),
                _fmt(item.rate_kg_per_rai),
                _fmt(item.total_kg),
                price,
                messages.item_description(item.key),
            )
        )

    total = sum(priced, Decimal(0))
    if priced:
        total_text = f"{_fmt(total)} {messages.CURRENCY}"
    else:
        total_text = messages.NO_PRICE
    if len(priced) < len(plan.items):
        total_text += f" ({PARTIAL_NOTE})"
    total_row = (TOTAL_LABEL, "", "", total_text, "")

    lines = [heading]
    for row in rows:
        name, per_rai, total_kg, price, desc = row
        lines.append(
            f"- {name}: {per_rai} กก./ไร่, รวม {total_kg} กก., "
            f"{messages.ESTIMATED_LABEL} {price} ({desc})"
        )
    lines.append(f"{TOTAL_LABEL} ({messages.ESTIMATED_LABEL}): {total_text}")
    return SummaryTable(
        heading=heading,
        columns=COLUMNS,
        rows=tuple(rows),
        total_row=total_row,
        text_version="\n".join(lines),
    )
