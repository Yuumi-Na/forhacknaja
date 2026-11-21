"""Pick the result path from the input source and the values. No network."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Literal

Path = Literal["sheet", "basic_formula", "ph_only"]

SHEET_RECOMMENDATIONS = "sheet_recommendations"


@dataclass(frozen=True)
class NeedMoreValues:
    """Not enough input for any path. `missing` lists the required fields still empty."""

    missing: tuple[str, ...]


def _is_present(v: Any) -> bool:
    return v is not None and v != "" and v != "unreadable"


def choose_path(
    source: str | None,
    values: Mapping[str, Any],
    sheet_recommendations: Sequence[Any],
    required_fields: Sequence[str],
) -> Path | NeedMoreValues:
    """Choose sheet, basic_formula, ph_only, or NeedMoreValues(missing).

    - lab_sheet with confirmed recommendations -> sheet
    - manual with every required field (pH optional) -> basic_formula
    - manual with only pH -> ph_only
    - manual with some values but not enough -> NeedMoreValues
    """
    if source == "lab_sheet":
        if sheet_recommendations:
            return "sheet"
        return NeedMoreValues((SHEET_RECOMMENDATIONS,))

    missing = tuple(f for f in required_fields if not _is_present(values.get(f)))
    if not missing:
        return "basic_formula"

    others_present = any(_is_present(v) for k, v in values.items() if k != "ph")
    if _is_present(values.get("ph")) and not others_present:
        return "ph_only"
    return NeedMoreValues(missing)
