"""Route tests for main.py with the vision stub on."""

import io

import pytest
from fastapi.testclient import TestClient

from mordin.main import MAX_UPLOAD_BYTES, create_app
from mordin.service import Service
from mordin.storage.store import InMemoryStore

JPEG = b"\xff\xd8\xff\xe0" + b"0" * 64
PNG = b"\x89PNG\r\n\x1a\n" + b"0" * 64


@pytest.fixture
def env():
    store = InMemoryStore()
    service = Service(store=store, stub=True)
    return TestClient(create_app(service)), store


def _start(client):
    r = client.post("/api/start")
    assert r.status_code == 200
    return r.json()


def _has_upload_button(body):
    return any(b["action"] == "upload_sheet" for bub in body["bubbles"] for b in bub["buttons"])


def test_start_returns_session_and_menu(env):
    client, _ = env
    body = _start(client)
    assert body["session_id"] and body["state"] and body["bubbles"]
    assert _has_upload_button(body)


def test_upload_jpeg_accepted(env):
    client, _ = env
    sid = _start(client)["session_id"]
    r = client.post(
        "/api/chat",
        data={"session_id": sid},
        files={"image": ("sheet.jpg", io.BytesIO(JPEG), "image/jpeg")},
    )
    body = r.json()
    assert r.status_code == 200
    assert body["state"] != "failed"
    assert body["session_id"]
    assert "ได้รับรูปแล้ว" in body["bubbles"][0]["text"]


def test_upload_png_accepted(env):
    client, _ = env
    sid = _start(client)["session_id"]
    r = client.post(
        "/api/chat",
        data={"session_id": sid},
        files={"image": ("sheet.png", io.BytesIO(PNG), "image/png")},
    )
    assert "ได้รับรูปแล้ว" in r.json()["bubbles"][0]["text"]


@pytest.mark.parametrize("content", [b"", b"GIF89a....", b"not an image"])
def test_bad_upload_rejected_without_new_session(env, content):
    client, store = env
    sid = _start(client)["session_id"]
    before = dict(getattr(store, "_sessions", {}))
    r = client.post(
        "/api/chat",
        data={"session_id": sid},
        files={"image": ("x.jpg", io.BytesIO(content), "image/jpeg")},
    )
    body = r.json()
    assert "ส่งรูป" in body["bubbles"][0]["text"]
    assert _has_upload_button(body)
    assert body["session_id"] == sid
    assert set(getattr(store, "_sessions", {})) == set(before)


def test_oversize_upload_rejected(env):
    client, store = env
    sid = _start(client)["session_id"]
    big = JPEG + b"0" * MAX_UPLOAD_BYTES
    r = client.post(
        "/api/chat",
        data={"session_id": sid},
        files={"image": ("big.jpg", io.BytesIO(big), "image/jpeg")},
    )
    body = r.json()
    assert "10 MB" in body["bubbles"][0]["text"]
    assert _has_upload_button(body)
    assert body["session_id"] == sid


def test_button_and_text_events(env):
    client, _ = env
    sid = _start(client)["session_id"]
    r = client.post("/api/chat", data={"session_id": sid, "action": "upload_sheet"})
    assert r.json()["bubbles"]
    r = client.post("/api/chat", data={"session_id": sid, "text": "สวัสดี"})
    assert r.status_code == 200 and r.json()["bubbles"]


def test_empty_turn_gets_error_bubble(env):
    client, _ = env
    sid = _start(client)["session_id"]
    r = client.post("/api/chat", data={"session_id": sid})
    assert r.status_code == 200
    assert r.json()["bubbles"][0]["buttons"][0]["action"] == "restart"


def test_unknown_session_gets_error_bubble(env):
    client, _ = env
    r = client.post("/api/chat", data={"session_id": "nope", "text": "x"})
    assert r.status_code == 200
    assert r.json()["bubbles"][0]["buttons"][0]["action"] == "restart"


def test_index_route(env):
    client, _ = env
    r = client.get("/")
    assert r.status_code == 200
    assert 'lang="th"' in r.text
