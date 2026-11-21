"""Half-up rounding with Decimal. Pure code, no network."""

from decimal import ROUND_HALF_UP, Decimal


def to_decimal(value: "Decimal | int | float | str") -> Decimal:
    """Convert to Decimal without binary float noise (floats go through str)."""
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def round_half_up(value: "Decimal | int | float | str", places: int = 0) -> Decimal:
    """Round to `places` decimal places, ties away from zero (0.05 -> 0.1)."""
    quantum = Decimal(1).scaleb(-places)
    return to_decimal(value).quantize(quantum, rounding=ROUND_HALF_UP)
