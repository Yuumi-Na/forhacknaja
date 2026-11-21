"""Conversation session. Pure data, no I/O, no image bytes, no personal data."""

from __future__ import annotations

from decimal import Decimal
from enum import StrEnum
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

Origin = Literal["read", "farmer"]
Source = Literal["lab_sheet", "manual"]
SoilValue = float | str | None


class State(StrEnum):
    IMAGE_RECEIVED = "image_received"
    VALUES_READ = "values_read"
    RETAKE_NEEDED = "retake_needed"
    CONFIRMED = "confirmed"
    AREA_REQUESTED = "area_requested"
    AREA_SET = "area_set"
    RESULT_SENT = "result_sent"
    CANCELLED = "cancelled"
    FAILED = "failed"


class SheetItem(BaseModel):
    """One fertilizer and rate (kg/rai) printed on the lab sheet."""

    fertilizer: str
    rate_kg_per_rai: Decimal
    origin: Origin = "read"


class Pending(BaseModel):
    """What the next typed text answers."""

    kind: Literal["area_answer", "correction_target", "correction_value", "manual_values"]
    field: str | None = None  # set for correction_value
    misses: int = 0  # invalid answers in a row for this step


class Session(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(default_factory=lambda: uuid4().hex)
    state: State = State.IMAGE_RECEIVED
    source: Source | None = None
    values: dict[str, SoilValue] = Field(default_factory=dict)
    # Per-value record: was the current value read by the model or typed by the farmer.
    value_origin: dict[str, Origin] = Field(default_factory=dict)
    sheet_recommendations: list[SheetItem] = Field(default_factory=list)
    area_rai: Decimal | None = None
    reads_failed_in_a_row: int = 0
    vision_retries: int = 0
    upload_name: str | None = None  # upload file name only; never image bytes
    pending: Pending | None = None

    def set_read_value(self, name: str, value: SoilValue) -> None:
        """Store a value read by the vision model."""
        self.values[name] = value
        self.value_origin[name] = "read"

    def set_farmer_value(self, name: str, value: SoilValue) -> None:
        """Store a value typed by the farmer (correction or manual entry)."""
        self.values[name] = value
        self.value_origin[name] = "farmer"
