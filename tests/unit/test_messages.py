"""explain/messages.py: every reply key used in flows/ has Thai text, and render() works."""

import re
from pathlib import Path

from mordin.explain import messages
from mordin.explain.messages import TH, render
from mordin.flows.types import ButtonSpec, Reply

FLOWS = Path(__file__).resolve().parents[2] / "src" / "mordin" / "flows"


def _flow_source() -> str:
    return "\n".join(p.read_text(encoding="utf-8") for p in FLOWS.glob("*.py"))


def test_every_reply_key_used_in_flows_exists_in_th():
    src = _flow_source()
    reply_keys = set(re.findall(r'Reply\(\s*"([a-z_.]+)"', src))
    reply_keys |= set(re.findall(r'key = "([a-z_.]+)"', src))
    reply_keys |= set(re.findall(r'else "([a-z_.]+)"', src))
    button_keys = {f"button.{k}" for k in re.findall(r'_btn\(\s*"([a-z_]+)"', src)}
    target_keys = {f"target.{k}" for k in re.findall(r'ButtonSpec\(\s*"target\.([a-z_]+)"', src)}
    target_keys |= {f"target.{n}" for n in ("om", "p", "k", "ca", "mg", "ph", "soil_texture")}
    assert len(reply_keys) >= 25  # the scan found the keys
    missing = (reply_keys | button_keys | target_keys) - set(TH)
    assert not missing


def test_keys_listed_in_reducer_docstring_exist_in_th():
    doc = (FLOWS / "reducer.py").read_text(encoding="utf-8").split('"""')[1]
    listed = set(re.findall(r"[a-z_]+\.[a-z_]+", doc.split("Reply keys used here:")[1]))
    assert listed
    assert listed <= set(TH)


def test_render_text_and_buttons():
    out = render(Reply("area.ask", buttons=[ButtonSpec("button.cancel", "cancel")]))
    assert out["kind"] == "buttons"
    assert "3 ไร่ 2 งาน" in out["text"]
    assert out["buttons"] == [{"label": "ยกเลิก", "action": "cancel", "payload": None}]
    assert render(Reply("input.choose_button"))["kind"] == "text"


def test_confirm_values_has_accuracy_sentence_and_rate_warning():
    params = {
        "values": {"om": 1.5, "ph": 5.4},
        "origins": {"om": "read", "ph": "farmer"},
        "items": [{"index": 1, "fertilizer": "urea", "rate_kg_per_rai": 250.0,
                   "origin": "read", "rate_warning": True}],
        "rate_max_kg_per_rai": 200.0,
    }
    text = render(Reply("confirm.values", params))["text"]
    assert messages.ACCURACY_CONFIRM in text
    assert "⚠" in text and "(คุณแก้ไข)" in text


def test_retake_names_unreadable_part_and_gives_tips():
    text = render(Reply("retake.message", {"unreadable": ["ph"], "reasons": {"ph": ""}}))["text"]
    assert "pH" in text and messages.RETAKE_TIPS in text


def test_area_accepted_shows_converted_value():
    text = render(Reply("area.accepted", {"input": "3 ไร่ 2 งาน", "area_rai": 3.5}))["text"]
    assert "3 ไร่ 2 งาน = 3.5 ไร่" in text


def test_descriptions_and_no_validated_claims():
    assert messages.item_description("urea")
    assert messages.item_description("15-15-15") == messages.GRADE_DESCRIPTION
    for word in ("รับรอง", "ตรวจสอบแล้ว", "ยืนยันความถูกต้อง", "การันตี"):
        assert word not in messages.ACCURACY_STARTUP + messages.ACCURACY_CONFIRM
    assert "ยังไม่ได้ทดสอบ" in messages.ACCURACY_STARTUP


def test_confirm_values_bubble_has_card_with_same_values():
    params = {
        "values": {"om": 1.73, "ph": 7.1, "soil_texture": "ร่วนปนดินเหนียว"},
        "origins": {"ph": "farmer"},
        "items": [{"index": 1, "fertilizer": "46-0-0", "rate_kg_per_rai": 20.98,
                   "origin": "read", "rate_warning": False}],
        "rate_max_kg_per_rai": 200.0,
    }
    bubble = render(Reply("confirm.values", params))
    card = bubble["card"]
    assert card["type"] == "confirm_values"
    assert [(f["name"], f["value"], f["edited"]) for f in card["fields"]] == [
        ("om", "1.73", False), ("ph", "7.1", True), ("soil_texture", "ร่วนปนดินเหนียว", False)
    ]
    assert card["items"][0]["rate"] == "20.98 กก./ไร่" and card["items"][0]["warning"] == ""
    assert "20.98" in bubble["text"]  # plain-text fallback is kept


def test_other_bubbles_have_no_card():
    assert "card" not in render(Reply("area.ask"))
