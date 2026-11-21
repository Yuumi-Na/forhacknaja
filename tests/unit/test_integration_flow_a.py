"""End-to-end flow A through the API: upload, confirm, field size, result (stub, no Bedrock)."""

import io
import re
from decimal import Decimal

from fastapi.testclient import TestClient
from PIL import Image

from mordin.explain import messages
from mordin.main import create_app
from mordin.service import Service
from mordin.storage.store import InMemoryStore

# demo_sheet_ok.json: urea 20.98 kg/rai, mop 12 kg/rai
RATES = [Decimal("20.98"), Decimal("12")]
AREA = Decimal("5")


def _png_bytes() -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (64, 64), "white").save(buf, format="PNG")
    return buf.getvalue()


def _actions(body):
    return {b["action"] for bub in body["bubbles"] for b in bub["buttons"]}


def test_flow_a_end_to_end():
    store = InMemoryStore()
    client = TestClient(create_app(Service(store=store, stub=True)))

    started = client.post("/api/start").json()
    assert started["stub"] is True
    sid = started["session_id"]

    # Upload a generated PNG named after the fixture.
    body = client.post(
        "/api/chat",
        data={"session_id": sid},
        files={"image": ("demo_sheet_ok.png", io.BytesIO(_png_bytes()), "image/png")},
    ).json()
    assert "confirm" in _actions(body)
    sid = body["session_id"]

    # Confirm the read values. The bot must ask the field size and show no total yet.
    body = client.post("/api/chat", data={"session_id": sid, "action": "confirm"}).json()
    assert not any(b["kind"] == "table" for b in body["bubbles"])
    sid = body["session_id"]

    # Answer the field size.
    body = client.post("/api/chat", data={"session_id": sid, "text": "5"}).json()
    assert body["state"] == "result_sent"
    bubbles = body["bubbles"]

    # Demo-data label shows.
    assert any(messages.DEMO_DATA_NOTICE in b["text"] for b in bubbles)

    # Table totals equal rate x 5 for each item.
    table = next(b for b in bubbles if b["kind"] == "table")["table"]
    assert "5" in table["heading"]
    assert len(table["rows"]) == len(RATES)
    for row, rate in zip(table["rows"], RATES):
        assert Decimal(row[1]) == rate
        assert Decimal(row[2]) == rate * AREA

    # Shop script: at most 3 sentences, with the rounded script_kg of each item.
    script = next(b for b in bubbles if b["text"].startswith(messages.SCRIPT_HEADING))
    text = script["text"][len(messages.SCRIPT_HEADING):].strip()
    sentences = [s for s in re.split(r"[.!?\n]+", text) if s.strip()]
    assert 1 <= len(sentences) <= 3
    for expected in ("105", "60"):  # 104.9 -> 105, 60.0 -> 60
        assert re.search(rf"(?<![\d.]){expected}(?![\d.])", text), expected
