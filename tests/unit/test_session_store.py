from decimal import Decimal

import pytest

from mordin.flows.session import Pending, Session, SheetItem, State
from mordin.storage.store import InMemoryStore, SessionNotFound


def test_states_cover_design():
    assert {s.value for s in State} == {
        "image_received", "values_read", "retake_needed", "confirmed",
        "area_requested", "area_set", "result_sent", "cancelled", "failed",
    }


def test_new_session_defaults():
    s = Session()
    assert s.state == State.IMAGE_RECEIVED
    assert s.area_rai is None
    assert s.reads_failed_in_a_row == 0 and s.vision_retries == 0
    assert s.pending is None and s.values == {}


def test_session_has_no_image_field():
    assert not any("image" in f and f != "state" for f in Session.model_fields)
    with pytest.raises(Exception):
        Session(image=b"x")


def test_origin_recorded_and_updated_on_correction():
    s = Session(source="lab_sheet")
    s.set_read_value("ph", 5.5)
    assert s.value_origin["ph"] == "read"
    s.set_farmer_value("ph", 6.0)
    assert s.values["ph"] == 6.0 and s.value_origin["ph"] == "farmer"


def test_store_roundtrip_and_isolation():
    store = InMemoryStore()
    s = Session(area_rai=Decimal("3.5"), pending=Pending(kind="area_answer"))
    s.sheet_recommendations.append(SheetItem(fertilizer="urea", rate_kg_per_rai=Decimal("20.98")))
    store.create(s)
    s.state = State.FAILED  # caller mutation must not leak into the store
    got = store.get(s.id)
    assert got.state == State.IMAGE_RECEIVED
    assert got.area_rai == Decimal("3.5")
    assert got.sheet_recommendations[0].rate_kg_per_rai == Decimal("20.98")
    got.state = State.CONFIRMED
    store.save(got)
    assert store.get(s.id).state == State.CONFIRMED


def test_store_missing_and_delete():
    store = InMemoryStore()
    with pytest.raises(SessionNotFound):
        store.get("nope")
    with pytest.raises(SessionNotFound):
        store.save(Session())
    s = Session()
    store.create(s)
    with pytest.raises(ValueError):
        store.create(s)
    store.delete(s.id)
    store.delete(s.id)  # deleting twice is fine
    with pytest.raises(SessionNotFound):
        store.get(s.id)
