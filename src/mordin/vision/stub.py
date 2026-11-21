"""Fixture reader that stands in for the Bedrock vision call. No network.

The fixture is chosen by the upload file name stem (e.g. "demo_sheet_low_k.jpg" reads
demo_sheet_low_k.json), else the default fixture. Fixtures are read from
<repo>/tests/fixtures, or from MORDIN_FIXTURES_DIR when set.
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path, PurePath

from mordin.vision.schemas import SheetReading

DEFAULT_FIXTURE = "demo_sheet_ok"
FIXTURES_DIR = Path(__file__).resolve().parents[3] / "tests" / "fixtures"
_STEM_RE = re.compile(r"^demo_[A-Za-z0-9_]+$")


def fixtures_dir() -> Path:
    override = os.environ.get("MORDIN_FIXTURES_DIR", "").strip()
    return Path(override) if override else FIXTURES_DIR


def read_lab_sheet_stub(filename: str | None, fixtures: Path | None = None) -> SheetReading:
    """Return the fixture matching the file name stem, else the default fixture."""
    base = Path(fixtures) if fixtures is not None else fixtures_dir()
    stem = PurePath((filename or "").replace("\\", "/")).stem
    name = stem if _STEM_RE.match(stem) and (base / f"{stem}.json").is_file() else DEFAULT_FIXTURE
    text = (base / f"{name}.json").read_text(encoding="utf-8")
    return SheetReading.model_validate(json.loads(text))
