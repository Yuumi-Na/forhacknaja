"""Output schema of the vision step. No I/O except loading limits.json (no network).

Each value is a number or the string "unreadable". Nothing is guessed.
"""

from __future__ import annotations

import json
from typing import Any, Literal

from pydantic import BaseModel, field_validator

from mordin.data import load_limits, normalize_texture

UNREADABLE = "unreadable"
NUMERIC_FIELDS = ("om", "p", "k", "ca", "mg", "ph")

Reading = float | Literal["unreadable"]
ReasonCode = Literal["not_dld_sheet", "blurry", "too_dark", "cropped", "unreadable"]


class SheetItem(BaseModel):
    """One fertilizer and rate (kg/rai) printed on the lab sheet."""

    fertilizer: str
    rate_kg_per_rai: Reading


class SheetReading(BaseModel):
    om: Reading = UNREADABLE
    p: Reading = UNREADABLE
    k: Reading = UNREADABLE
    ca: Reading = UNREADABLE
    mg: Reading = UNREADABLE
    ph: Reading = UNREADABLE
    soil_texture: str = UNREADABLE
    sheet_recommendations: list[SheetItem] | Literal["unreadable"] = UNREADABLE
    reason_code: ReasonCode | None = None

    @field_validator("sheet_recommendations", mode="before")
    @classmethod
    def _decode_json_list(cls, value: Any) -> Any:
        """Accept the list sent as a JSON string, which the model often does.

        The string is only decoded. Anything that is not a JSON list is left for
        normal validation to reject, so no value is guessed.
        """
        if isinstance(value, str) and value.strip().startswith("["):
            try:
                decoded = json.loads(value)
            except ValueError:
                return value
            if isinstance(decoded, list):
                return decoded
        return value


def validate_reading(
    reading: SheetReading, limits: dict[str, Any] | None = None
) -> SheetReading:
    """Return a copy where out-of-range numbers and unknown textures are "unreadable".

    A known texture printed with a leading "ดิน" is mapped to its name in limits.json.
    """
    limits = load_limits() if limits is None else limits
    ranges = limits["valid_ranges"]
    textures = limits["soil_textures"]

    updates: dict[str, Any] = {}
    for name in NUMERIC_FIELDS:
        value = getattr(reading, name)
        if value == UNREADABLE:
            continue
        rng = ranges.get(name)
        if rng is not None and not (rng["min"] <= value <= rng["max"]):
            updates[name] = UNREADABLE
    if reading.soil_texture != UNREADABLE:
        texture = normalize_texture(reading.soil_texture, textures)
        updates["soil_texture"] = texture if texture is not None else UNREADABLE
    return reading.model_copy(update=updates)
