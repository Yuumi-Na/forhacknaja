"""Load and validate the files under data/ (no network).

A bad file raises DataFileError(path, reason), which names the file.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

DATA_DIR = Path(__file__).resolve().parents[2] / "data"

PRICES_FILE = "fertilizer_prices.json"
FORMULA_FILE = "dld_rules/basic_formula.json"
LIMITS_FILE = "limits.json"
AMENDMENTS_FILE = "soil_amendments.json"
PH_CLASSES = ("acidic", "balanced", "alkaline")

STATUSES = ("good", "fair", "low", "needs_action")
REQUIRED_MAX_KG = ("urea", "dap", "mop")
TARGET_KEYS = {
    "om": "target_n_kg_per_rai",
    "p": "target_p2o5_kg_per_rai",
    "k": "target_k2o_kg_per_rai",
}


class DataFileError(Exception):
    """A data file is missing or invalid. `path` names the file."""

    def __init__(self, path: str | Path, reason: str) -> None:
        self.path = str(path)
        self.reason = reason
        super().__init__(f"{self.path}: {reason}")


@dataclass(frozen=True)
class Data:
    prices: dict[str, Any]
    basic_formula: dict[str, Any]
    limits: dict[str, Any]
    amendments: dict[str, Any]


def _read_json(path: Path) -> dict[str, Any]:
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        raise DataFileError(path, "file not found") from None
    except OSError as exc:
        raise DataFileError(path, f"cannot read file: {exc}") from None
    try:
        obj = json.loads(text)
    except json.JSONDecodeError as exc:
        raise DataFileError(path, f"invalid JSON: {exc}") from None
    if not isinstance(obj, dict):
        raise DataFileError(path, "top level must be a JSON object")
    return obj


def _is_number(v: Any) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def _check_label(path: Path, obj: dict[str, Any]) -> None:
    label = obj.get("label")
    if obj.get("placeholder") is True and (not isinstance(label, str) or not label.strip()):
        raise DataFileError(path, "placeholder file needs a non-empty label")


def _require(path: Path, obj: dict[str, Any], key: str, typ: type) -> Any:
    if key not in obj:
        raise DataFileError(path, f"missing key '{key}'")
    if not isinstance(obj[key], typ):
        raise DataFileError(path, f"'{key}' must be {typ.__name__}")
    return obj[key]


def load_prices(data_dir: Path = DATA_DIR) -> dict[str, Any]:
    path = Path(data_dir) / PRICES_FILE
    obj = _read_json(path)
    _check_label(path, obj)
    _require(path, obj, "date", str)
    prices = _require(path, obj, "prices_per_kg", dict)
    for name, price in prices.items():
        if price is not None and (not _is_number(price) or price < 0):
            raise DataFileError(path, f"price for '{name}' must be a number >= 0 or null")
    return obj


def load_limits(data_dir: Path = DATA_DIR) -> dict[str, Any]:
    path = Path(data_dir) / LIMITS_FILE
    obj = _read_json(path)
    _check_label(path, obj)
    ranges = _require(path, obj, "valid_ranges", dict)
    for field, rng in ranges.items():
        if (
            not isinstance(rng, dict)
            or not _is_number(rng.get("min"))
            or not _is_number(rng.get("max"))
            or rng["min"] > rng["max"]
        ):
            raise DataFileError(path, f"valid_ranges['{field}'] needs numeric min <= max")
    textures = _require(path, obj, "soil_textures", list)
    if not textures or not all(isinstance(t, str) and t for t in textures):
        raise DataFileError(path, "'soil_textures' must be a non-empty list of strings")
    rate = _require(path, obj, "sheet_rate_kg_per_rai", dict)
    if not _is_number(rate.get("max")) or rate["max"] <= 0:
        raise DataFileError(path, "'sheet_rate_kg_per_rai.max' must be a number > 0")
    bag = obj.get("small_bag_kg")
    if not _is_number(bag) or bag <= 0:
        raise DataFileError(path, "'small_bag_kg' must be a number > 0")
    return obj


def load_basic_formula(data_dir: Path = DATA_DIR) -> dict[str, Any]:
    path = Path(data_dir) / FORMULA_FILE
    obj = _read_json(path)
    _check_label(path, obj)

    max_kg = obj.get("max_kg_per_rai")
    if not isinstance(max_kg, dict):
        raise DataFileError(path, "missing 'max_kg_per_rai' for urea, dap, mop")
    for name in REQUIRED_MAX_KG:
        v = max_kg.get(name)
        if not _is_number(v) or v <= 0:
            raise DataFileError(path, f"missing or invalid max_kg_per_rai for '{name}'")

    required = _require(path, obj, "required_fields", list)
    bands = _require(path, obj, "bands", dict)
    for field in required:
        if field not in bands:
            raise DataFileError(path, f"required field '{field}' has no bands")
    if not _is_number(obj.get("p_sufficient")):
        raise DataFileError(path, "'p_sufficient' must be a number")

    texture = obj.get("texture_status")
    if texture is not None:
        if not isinstance(texture, dict) or any(s not in STATUSES for s in texture.values()):
            raise DataFileError(path, f"'texture_status' values must be one of {STATUSES}")

    for field, rows in bands.items():
        if not isinstance(rows, list) or not rows:
            raise DataFileError(path, f"bands['{field}'] must be a non-empty list")
        mins = []
        for row in rows:
            if not isinstance(row, dict) or not _is_number(row.get("min")):
                raise DataFileError(path, f"bands['{field}'] rows need a numeric 'min'")
            if "status" in row and row["status"] not in STATUSES:
                raise DataFileError(path, f"bands['{field}'] status must be one of {STATUSES}")
            mins.append(row["min"])
        if any(b <= a for a, b in zip(mins, mins[1:])):
            raise DataFileError(path, f"bands['{field}'] 'min' values must strictly increase")
        key = TARGET_KEYS.get(field)
        if key is None:
            continue
        targets = []
        for row in rows:
            t = row.get(key)
            if not _is_number(t) or t < 0:
                raise DataFileError(path, f"bands['{field}'] row needs '{key}' >= 0")
            targets.append(t)
        if any(b > a for a, b in zip(targets, targets[1:])):
            raise DataFileError(
                path, f"bands['{field}'] is not monotone: a higher soil level raises '{key}'"
            )
    return obj


def load_amendments(data_dir: Path = DATA_DIR) -> dict[str, Any]:
    path = Path(data_dir) / AMENDMENTS_FILE
    obj = _read_json(path)
    _check_label(path, obj)
    limits = _require(path, obj, "ph_limits", dict)
    lo, hi = limits.get("acidic_below"), limits.get("alkaline_above")
    if not _is_number(lo) or not _is_number(hi) or lo > hi:
        raise DataFileError(path, "'ph_limits' needs numeric acidic_below <= alkaline_above")
    materials = _require(path, obj, "materials", dict)
    for cls in PH_CLASSES:
        if cls not in materials:
            raise DataFileError(path, f"missing materials for pH class '{cls}'")
    for cls, rows in materials.items():
        if cls not in PH_CLASSES:
            raise DataFileError(path, f"unknown pH class '{cls}'")
        if not isinstance(rows, list):
            raise DataFileError(path, f"materials['{cls}'] must be a list")
        for row in rows:
            if not isinstance(row, dict) or not isinstance(row.get("key"), str) or not row["key"]:
                raise DataFileError(path, f"materials['{cls}'] rows need a 'key'")
            rate, mx = row.get("rate_kg_per_rai"), row.get("max_rate_kg_per_rai")
            if not _is_number(rate) or rate < 0:
                raise DataFileError(path, f"'{row['key']}' needs rate_kg_per_rai >= 0")
            if not _is_number(mx) or mx < rate:
                raise DataFileError(
                    path, f"'{row['key']}' needs max_rate_kg_per_rai >= rate_kg_per_rai"
                )
    return obj


_TEXTURE_PREFIX = "ดิน"


def normalize_texture(text: str, textures: list[str]) -> str | None:
    """Return the matching name from `textures`, or None.

    DLD sheets may print the texture with a leading "ดิน" (e.g. "ดินร่วนปนดินเหนียว"
    for "ร่วนปนดินเหนียว"). An exact match wins, so "ดินเหนียว" stays as it is.
    """
    value = "".join(text.split())
    if value in textures:
        return value
    if value.startswith(_TEXTURE_PREFIX) and value[len(_TEXTURE_PREFIX):] in textures:
        return value[len(_TEXTURE_PREFIX):]
    return None


def load_data(data_dir: Path = DATA_DIR) -> Data:
    """Load and validate every file this module owns."""
    return Data(
        amendments=load_amendments(data_dir),
        prices=load_prices(data_dir),
        basic_formula=load_basic_formula(data_dir),
        limits=load_limits(data_dir),
    )
