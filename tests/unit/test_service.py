import io
import logging

from PIL import Image

from mordin.data import load_data
from mordin.flows import Button, ImageUploaded, State, Text
from mordin.service import ImageHolder, Service
from mordin.storage.store import InMemoryStore
from mordin.vision import reader
from mordin.vision.schemas import SheetItem as VItem
from mordin.vision.schemas import SheetReading

DATA = load_data()
GOOD = SheetReading(
    om=1.2, p=8, k=60, ca=400, mg=70, ph=5.4, soil_texture="ร่วนทราย",
    sheet_recommendations=[VItem(fertilizer="15-15-15", rate_kg_per_rai=50)],
)


def jpeg() -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (40, 40), "white").save(buf, format="JPEG")
    return buf.getvalue()


def texts(out):
    return " ".join(b["text"] for b in out["bubbles"])


def test_stub_flow_confirm_and_area_gives_table_and_script():
    svc = Service(InMemoryStore(), DATA, stub=True)
    sid = svc.start()["session_id"]
    out = svc.handle(sid, ImageUploaded("demo_sheet_ok.jpg"))
    assert out["state"] == State.VALUES_READ.value
    out = svc.handle(sid, Button("confirm"))
    assert out["state"] == State.AREA_REQUESTED.value
    out = svc.handle(sid, Text("5"))
    assert out["state"] == State.RESULT_SENT.value
    kinds = [b["kind"] for b in out["bubbles"]]
    assert "table" in kinds and "advice" in kinds


def test_restart_creates_new_session_and_drops_old():
    store = InMemoryStore()
    svc = Service(store, DATA, stub=True)
    sid = svc.start()["session_id"]
    out = svc.handle(sid, Text("restart"))
    assert out["session_id"] != sid
    assert store.get(out["session_id"])


def _patch_reader(monkeypatch, results):
    calls = []

    def fake(img, data):
        calls.append(img)
        r = results.pop(0)
        if isinstance(r, Exception):
            raise r
        return r

    monkeypatch.setattr(reader, "read_lab_sheet", fake)
    return calls


def test_image_held_while_retry_possible_then_deleted(monkeypatch):
    err = reader.ReadError("boom")
    _patch_reader(monkeypatch, [err, GOOD])
    svc = Service(InMemoryStore(), DATA, stub=False)
    sid = svc.start()["session_id"]
    out = svc.handle(sid, ImageUploaded("a.jpg"), image=jpeg())
    assert out["state"] == State.IMAGE_RECEIVED.value
    assert sid in svc.holder
    out = svc.handle(sid, Button("retry_read"))
    assert out["state"] == State.VALUES_READ.value
    assert sid not in svc.holder


def test_image_deleted_after_retries_run_out(monkeypatch):
    _patch_reader(monkeypatch, [reader.ReadError("x")] * 3)
    svc = Service(InMemoryStore(), DATA, stub=False)
    sid = svc.start()["session_id"]
    svc.handle(sid, ImageUploaded("a.jpg"), image=jpeg())
    svc.handle(sid, Button("retry_read"))
    assert sid in svc.holder
    svc.handle(sid, Button("retry_read"))
    assert sid not in svc.holder


def test_image_deleted_on_cancel(monkeypatch):
    _patch_reader(monkeypatch, [reader.ReadError("x")])
    svc = Service(InMemoryStore(), DATA, stub=False)
    sid = svc.start()["session_id"]
    svc.handle(sid, ImageUploaded("a.jpg"), image=jpeg())
    assert sid in svc.holder
    svc.handle(sid, Button("cancel"))
    assert sid not in svc.holder


def test_error_logs_hold_no_values_or_image(monkeypatch, caplog):
    _patch_reader(monkeypatch, [reader.ReadError("secret ph 5.4 bytes")])
    svc = Service(InMemoryStore(), DATA, stub=False)
    sid = svc.start()["session_id"]
    with caplog.at_level(logging.INFO, logger="mordin.service"):
        svc.handle(sid, ImageUploaded("a.jpg"), image=jpeg())
    errors = [r.getMessage() for r in caplog.records if r.levelno == logging.ERROR]
    assert errors == [f"failure step=read session={sid} type=ReadError"]


def test_store_error_shows_generic_bubble_with_restart(caplog):
    class Broken(InMemoryStore):
        def save(self, s):
            raise OSError("disk")

    svc = Service(Broken(), DATA, stub=True)
    sid = svc.start()["session_id"]
    with caplog.at_level(logging.ERROR, logger="mordin.service"):
        out = svc.handle(sid, ImageUploaded("demo_sheet_ok.jpg"))
    bubble = out["bubbles"][0]
    assert "ระบบขัดข้อง" in bubble["text"]
    assert [b["action"] for b in bubble["buttons"]] == ["restart"]
    assert "type=OSError" in caplog.text


def test_unknown_session_shows_generic_bubble():
    out = Service(InMemoryStore(), DATA, stub=True).handle("nope", Text("x"))
    assert out["bubbles"][0]["buttons"][0]["action"] == "restart"


def test_slow_turn_logs_warning(caplog):
    ticks = iter(range(0, 1000, 40))
    svc = Service(InMemoryStore(), DATA, stub=True, clock=lambda: float(next(ticks)))
    sid = svc.start()["session_id"]
    with caplog.at_level(logging.WARNING, logger="mordin.service"):
        svc.handle(sid, Text("hello"))
    assert "turn over 30 s" in caplog.text


def test_holder_basic():
    h = ImageHolder()
    h.put("a", object())  # type: ignore[arg-type]
    h.move("a", "b")
    assert "b" in h and "a" not in h
    h.delete("b")
    assert "b" not in h
