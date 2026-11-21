"""Basic sugarcane formula helpers. Pure code, no network.

soil_status: one status (good, fair, low, needs_action) per soil value,
read from the bands in data/dld_rules/basic_formula.json (F3, Req 13.2).
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Mapping

from mordin.fertilizer.rounding import round_half_up, to_decimal

NUMERIC_FIELDS = ("om", "p", "k", "ca", "mg", "ph")

# Nutrient content (fraction of weight) of urea 46-0-0, DAP 18-46-0, MOP 0-0-60.
UREA_N = Decimal("0.46")
DAP_N = Decimal("0.18")
DAP_P2O5 = Decimal("0.46")
MOP_K2O = Decimal("0.60")


class FormulaError(ValueError):
    """Basic formula cannot run. `field` names the offending or missing value."""

    def __init__(self, field: str, reason: str):
        super().__init__(f"{field}: {reason}")
        self.field = field
        self.reason = reason


@dataclass(frozen=True)
class BasicResult:
    amounts_kg_per_rai: dict[str, Decimal]  # urea, dap, mop, whole kg
    supplied_kg_per_rai: dict[str, Decimal]  # n, p2o5, k2o, 0.1 kg
    label: str  # Demo_Rules_Label


def _is_number(v: Any) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def _band_status(rows: list[dict[str, Any]], value: float) -> str | None:
    """Status of the last band whose `min` is at or below the value."""
    status = None
    for row in rows:
        if value >= row["min"]:
            status = row.get("status")
        else:
            break
    return status


def soil_status(values: Mapping[str, Any], rules: Mapping[str, Any]) -> dict[str, str]:
    """Return {field: status} for every value that is present.

    Values that are None, "unreadable" or not a number are skipped. A texture
    that is not listed in `texture_status` is skipped too (no status is invented).
    """
    result: dict[str, str] = {}
    bands = rules.get("bands", {})
    for field in NUMERIC_FIELDS:
        value = values.get(field)
        rows = bands.get(field)
        if not _is_number(value) or not rows:
            continue
        status = _band_status(rows, value)
        if status is not None:
            result[field] = status
    texture = values.get("soil_texture")
    if isinstance(texture, str):
        status = rules.get("texture_status", {}).get(texture)
        if status is not None:
            result["soil_texture"] = status
    return result


def _band_row(rows: list[dict[str, Any]], value: float) -> dict[str, Any]:
    """The last band whose `min` is at or below the value."""
    chosen = rows[0]
    for row in rows:
        if value >= row["min"]:
            chosen = row
        else:
            break
    return chosen


def _check_ranges(values: Mapping[str, Any], limits: Mapping[str, Any]) -> None:
    for field, rng in limits.get("valid_ranges", {}).items():
        value = values.get(field)
        if not _is_number(value):
            continue
        if not (rng["min"] <= value <= rng["max"]):
            raise FormulaError(field, "out of valid range")


def calculate_basic(
    values: Mapping[str, Any],
    rules: Mapping[str, Any],
    limits: Mapping[str, Any] | None = None,
) -> BasicResult:
    """Urea, DAP and MOP in kg per rai from typed soil values (F3, Req 9).

    Raises FormulaError for a missing required field or, when `limits` is given,
    a value outside its valid range. No network, no model call.
    """
    if limits is not None:
        _check_ranges(values, limits)
    for field in rules["required_fields"]:
        if not _is_number(values.get(field)):
            raise FormulaError(field, "missing")

    bands = rules["bands"]
    n_target = to_decimal(_band_row(bands["om"], values["om"])["target_n_kg_per_rai"])
    k2o_target = to_decimal(_band_row(bands["k"], values["k"])["target_k2o_kg_per_rai"])
    if values["p"] >= rules["p_sufficient"]:
        p2o5_target = Decimal(0)
    else:
        p2o5_target = to_decimal(_band_row(bands["p"], values["p"])["target_p2o5_kg_per_rai"])

    dap = p2o5_target / DAP_P2O5
    urea = max(Decimal(0), n_target - dap * DAP_N) / UREA_N
    mop = k2o_target / MOP_K2O

    caps = rules["max_kg_per_rai"]
    amounts: dict[str, Decimal] = {}
    for key, raw in (("urea", urea), ("dap", dap), ("mop", mop)):
        kg = round_half_up(raw, 0)
        amounts[key] = min(max(kg, Decimal(0)), to_decimal(caps[key]))

    supplied = {
        "n": round_half_up(amounts["urea"] * UREA_N + amounts["dap"] * DAP_N, 1),
        "p2o5": round_half_up(amounts["dap"] * DAP_P2O5, 1),
        "k2o": round_half_up(amounts["mop"] * MOP_K2O, 1),
    }
    return BasicResult(amounts, supplied, rules["label"])
