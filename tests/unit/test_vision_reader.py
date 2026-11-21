import re
import time
from types import SimpleNamespace

import pytest

import mordin.vision.reader as reader
from mordin.data import load_data
from mordin.vision.image import PreparedImage
from mordin.vision.schemas import SheetItem, SheetReading

IMG = PreparedImage(b"\xff\xd8\xff fake", "jpeg", 10, 10)


class FakeAgent:
    def __init__(self, output=None, error=None, delay=0.0):
        self.output, self.error, self.delay = output, error, delay
        self.calls = []

    def __call__(self, content, **kwargs):
        self.calls.append((content, kwargs))
        if self.delay:
            time.sleep(self.delay)
        if self.error:
            raise self.error
        return SimpleNamespace(structured_output=self.output)


def _patch(monkeypatch, agent):
    built = []

    def build(system_prompt):
        built.append(system_prompt)
        return agent

    monkeypatch.setattr(reader, "_build_agent", build)
    return built


def test_read_sends_image_block_and_schema(monkeypatch):
    out = SheetReading(
        om=2.1, p=12, k=80, ca=900, mg=100, ph=5.6, soil_texture="ร่วน",
        sheet_recommendations=[SheetItem(fertilizer="46-0-0", rate_kg_per_rai=20.98)],
    )
    agent = FakeAgent(out)
    built = _patch(monkeypatch, agent)
    result = reader.read_lab_sheet(IMG, load_data())
    content, kwargs = agent.calls[0]
    assert kwargs["structured_output_model"] is SheetReading
    assert content[1]["image"]["format"] == "jpeg"
    assert content[1]["image"]["source"]["bytes"] == IMG.data
    assert built and "DLD" in built[0]
    assert result.sheet_recommendations[0].rate_kg_per_rai == 20.98


def test_out_of_range_value_marked_unreadable(monkeypatch):
    _patch(monkeypatch, FakeAgent(SheetReading(ph=99.0, soil_texture="ร่วน")))
    assert reader.read_lab_sheet(IMG, load_data()).ph == "unreadable"


def test_fresh_agent_per_call(monkeypatch):
    built = _patch(monkeypatch, FakeAgent(SheetReading()))
    reader.read_lab_sheet(IMG, load_data())
    reader.read_lab_sheet(IMG, load_data())
    assert len(built) == 2


def test_model_error_becomes_read_error(monkeypatch):
    _patch(monkeypatch, FakeAgent(error=RuntimeError("boom")))
    with pytest.raises(reader.ReadError):
        reader.read_lab_sheet(IMG, load_data())


def test_missing_structured_output_is_read_error(monkeypatch):
    _patch(monkeypatch, FakeAgent(output=None))
    with pytest.raises(reader.ReadError):
        reader.read_lab_sheet(IMG, load_data())


def test_deadline(monkeypatch):
    monkeypatch.setattr(reader, "DEADLINE_SECONDS", 0.1)
    _patch(monkeypatch, FakeAgent(SheetReading(), delay=0.5))
    with pytest.raises(reader.ReadError):
        reader.read_lab_sheet(IMG, load_data())


def test_prompt_has_no_arithmetic_or_adjustment():
    text = reader.load_prompt().lower()
    for word in ("multiply", "convert", "round", "adjust", "recalculate", "increase", "decrease"):
        assert not re.search(rf"\b{word}\b", text)
    assert "unreadable" in text and "blurry" in text and "not_dld_sheet" in text
    for field in ("om", "p", "k", "ca", "mg", "ph", "soil_texture", "rate_kg_per_rai"):
        assert field in text
