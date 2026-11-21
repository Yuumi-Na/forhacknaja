"""Parse the farmer's field size into `area_rai`. Pure code, no network."""

import re
from decimal import Decimal, InvalidOperation

from mordin.fertilizer.rounding import round_half_up

# 1 rai = 4 ngan = 400 sq wa = 1600 m2; 1 hectare = 6.25 rai.
_RAI_PER_UNIT: dict[str, Decimal] = {
    "rai": Decimal(1),
    "ngan": Decimal(1) / Decimal(4),
    "sqwa": Decimal(1) / Decimal(400),
    "sqm": Decimal(1) / Decimal(1600),
    "hectare": Decimal("6.25"),
}

_UNIT_ALIASES: dict[str, str] = {
    "ไร่": "rai",
    "rai": "rai",
    "งาน": "ngan",
    "ngan": "ngan",
    "ตารางวา": "sqwa",
    "ตร.ว.": "sqwa",
    "ตร.ว": "sqwa",
    "ตรว": "sqwa",
    "sqwa": "sqwa",
    "ตารางเมตร": "sqm",
    "ตร.ม.": "sqm",
    "ตร.ม": "sqm",
    "ตรม": "sqm",
    "m2": "sqm",
    "m²": "sqm",
    "sqm": "sqm",
    "เฮกตาร์": "hectare",
    "เฮกเตอร์": "hectare",
    "hectare": "hectare",
    "hectares": "hectare",
    "ha": "hectare",
}

_THAI_DIGITS = str.maketrans("๐๑๒๓๔๕๖๗๘๙", "0123456789")
_PART = re.compile(r"\s*(\d+(?:\.\d+)?)\s*([^\d\s]*)")


class AreaError(ValueError):
    """The field size answer cannot be used."""


def parse_area(text: str) -> float:
    """Convert a field size answer to `area_rai` (rai, 4 decimals, half up)."""
    if not isinstance(text, str):
        raise AreaError("not text")
    s = text.translate(_THAI_DIGITS).strip().lower().replace(",", "")
    s = re.sub(r"(?<![a-z])m\s*[2²]", "sqm", s)  # "m2" contains a digit, so map it first
    if not s:
        raise AreaError("empty")
    if s.startswith("-"):
        raise AreaError("negative")

    pos = 0
    parts: list[tuple[Decimal, str | None]] = []
    while pos < len(s):
        m = _PART.match(s, pos)
        if not m:
            raise AreaError("not a number")
        try:
            number = Decimal(m.group(1))
        except InvalidOperation as exc:  # pragma: no cover
            raise AreaError("not a number") from exc
        unit_text = m.group(2)
        unit = None
        if unit_text:
            unit = _UNIT_ALIASES.get(unit_text)
            if unit is None:
                raise AreaError(f"unknown unit: {unit_text}")
        parts.append((number, unit))
        pos = m.end()

    if len(parts) == 1 and parts[0][1] is None:
        parts[0] = (parts[0][0], "rai")
    seen: set[str] = set()
    total = Decimal(0)
    for number, unit in parts:
        if unit is None:
            raise AreaError("number without a unit in a combined answer")
        if unit in seen:
            raise AreaError(f"repeated unit: {unit}")
        seen.add(unit)
        total += number * _RAI_PER_UNIT[unit]

    if total <= 0:
        raise AreaError("area must be greater than zero")
    result = round_half_up(total, 4)
    if result <= 0:
        raise AreaError("area is too small")
    return float(result)
