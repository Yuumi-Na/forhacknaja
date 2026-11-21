"""Figure guard and wording check for model-written text. Pure code, no network, no arithmetic.

A figure is a number written next to a weight, money, area, bag or percent unit. The model may
only repeat figures the code gave it (Req 13.7, 13.8).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Collection, Mapping

WEIGHT = "weight"
MONEY = "money"
AREA = "area"
BAG = "bag"
PERCENT = "percent"

_UNITS: dict[str, str] = {
    "กิโลกรัม": WEIGHT,
    "กิโล": WEIGHT,
    "กก": WEIGHT,
    "กรัม": WEIGHT,
    "ตัน": WEIGHT,
    "kg": WEIGHT,
    "kgs": WEIGHT,
    "บาท": MONEY,
    "baht": MONEY,
    "thb": MONEY,
    "ตารางวา": AREA,
    "ไร่": AREA,
    "งาน": AREA,
    "rai": AREA,
    "ถุง": BAG,
    "bag": BAG,
    "bags": BAG,
    "%": PERCENT,
    "เปอร์เซ็นต์": PERCENT,
}
_UNIT_ALT = "|".join(re.escape(u) for u in sorted(_UNITS, key=len, reverse=True))
_NUM = r"\d[\d,]*(?:\.\d+)?"
_AFTER = re.compile(rf"(?P<num>{_NUM})\s*(?P<unit>{_UNIT_ALT})\.?(?![a-zA-Z])", re.IGNORECASE)
_BAHT_SIGN = re.compile(rf"฿\s*(?P<num>{_NUM})")

FORBIDDEN_WORDS: tuple[str, ...] = (
    "รับรอง",
    "รับประกัน",
    "แน่นอน",
    "ตรวจสอบแล้ว",
    "ยืนยันแล้ว",
    "verified",
    "guarantee",
)
_YIELD_NUMBER = re.compile(r"ผลผลิต[^\n.]{0,30}\d|\d[^\n.]{0,30}ผลผลิต|yield[^\n.]{0,30}\d", re.IGNORECASE)


@dataclass(frozen=True)
class Figure:
    text: str
    value: Decimal
    kind: str  # weight, money, area, bag or percent


def _to_decimal(raw: str) -> Decimal | None:
    try:
        return Decimal(raw.replace(",", ""))
    except InvalidOperation:
        return None


def find_figures(text: str) -> list[Figure]:
    """Every number that sits next to a weight, money, area, bag or percent unit."""
    found: list[Figure] = []
    for m in _AFTER.finditer(text):
        value = _to_decimal(m.group("num"))
        if value is not None:
            found.append(Figure(m.group(0), value, _UNITS[m.group("unit").lower()]))
    for m in _BAHT_SIGN.finditer(text):
        value = _to_decimal(m.group("num"))
        if value is not None:
            found.append(Figure(m.group(0), value, MONEY))
    return found


def _decimals(values: Collection[object]) -> set[Decimal]:
    out: set[Decimal] = set()
    for v in values:
        try:
            out.add(Decimal(str(v)))
        except InvalidOperation:
            continue
    return out


def check_figures(text: str, allowed: Mapping[str, Collection[object]] | None = None) -> list[str]:
    """Return the figures in `text` that are not in `allowed` (empty list means the text passes).

    `allowed` maps a kind (weight, money, area, bag, percent) to the values the code produced.
    Bag and percent figures are never allowed. With no `allowed`, any figure fails.
    """
    allowed = allowed or {}
    bad: list[str] = []
    for fig in find_figures(text):
        if fig.kind in (BAG, PERCENT):
            bad.append(fig.text)
        elif fig.value not in _decimals(allowed.get(fig.kind, ())):
            bad.append(fig.text)
    return bad


def check_wording(text: str) -> list[str]:
    """Return wording problems: promise or "verified" words and yield numbers."""
    low = text.lower()
    problems = [w for w in FORBIDDEN_WORDS if w in low]
    if _YIELD_NUMBER.search(text):
        problems.append("yield_number")
    return problems
