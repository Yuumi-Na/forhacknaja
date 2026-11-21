"""Thai farmer-facing text for the chat page. No fertilizer arithmetic here.

Every reply key that `flows/` can return has an entry in `TH`. An entry is a plain string or a
function of the reply params. `render(reply)` turns a `Reply` spec into a bubble the page shows.
Keep the keys when English is added later: a second dict with the same keys is enough.
"""

from __future__ import annotations

from typing import Any, Callable

from mordin.flows.types import ButtonSpec, Reply

Params = dict[str, Any]
Entry = str | Callable[[Params], str]


# --- small formatting helpers (display only) ----------------------------------------
def _num(v: Any) -> str:
    """Show a number without a trailing .0."""
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        return f"{v:.4f}".rstrip("0").rstrip(".") if v != int(v) else str(int(v))
    return str(v)


def _range_text(p: Params) -> str:
    return f"{_num(p.get('min'))} ถึง {_num(p.get('max'))}"


# --- fixed texts --------------------------------------------------------------------
FIELD_LABELS: dict[str, str] = {
    "om": "อินทรียวัตถุ (OM) %",
    "p": "ฟอสฟอรัส (P) มก./กก.",
    "k": "โพแทสเซียม (K) มก./กก.",
    "ca": "แคลเซียม (Ca) มก./กก.",
    "mg": "แมกนีเซียม (Mg) มก./กก.",
    "ph": "ค่าความเป็นกรดด่าง (pH)",
    "soil_texture": "เนื้อดิน",
    "sheet_recommendations": "สูตรปุ๋ยและอัตราที่ใบวิเคราะห์แนะนำ",
}

ITEM_NAMES: dict[str, str] = {
    "urea": "ยูเรีย (46-0-0)",
    "dap": "ไดแอมโมเนียมฟอสเฟต (18-46-0)",
    "mop": "โพแทสเซียมคลอไรด์ (0-0-60)",
    "agri_lime": "ปูนขาวปรับปรุงดิน",
    "dolomite": "โดโลไมต์",
}

# Fixed per-fertilizer text. Never written by a model.
ITEM_DESCRIPTIONS: dict[str, str] = {
    "urea": "ให้ธาตุไนโตรเจน ช่วยให้ต้นและใบอ้อยเจริญเติบโต",
    "dap": "ให้ธาตุฟอสฟอรัสและไนโตรเจน ช่วยให้รากและการแตกกอดี",
    "mop": "ให้ธาตุโพแทสเซียม ช่วยให้ลำอ้อยสะสมน้ำตาล",
    "agri_lime": "ช่วยลดความเป็นกรดของดิน",
    "dolomite": "ช่วยลดความเป็นกรดของดิน และเพิ่มแคลเซียมกับแมกนีเซียม",
}
GRADE_DESCRIPTION = "ปุ๋ยสูตรผสมตามที่ใบวิเคราะห์ดินแนะนำ"
UNKNOWN_DESCRIPTION = "ใช้ตามที่ใบวิเคราะห์ดินแนะนำ"


def item_name(key: str) -> str:
    """Display name for a fertilizer or material key. A grade such as 15-15-15 shows as is."""
    if key in ITEM_NAMES:
        return ITEM_NAMES[key]
    return f"ปุ๋ยสูตร {key}"


def item_description(key: str) -> str:
    if key in ITEM_DESCRIPTIONS:
        return ITEM_DESCRIPTIONS[key]
    parts = key.split("-")
    if len(parts) == 3 and all(x.isdigit() for x in parts):
        return GRADE_DESCRIPTION
    return UNKNOWN_DESCRIPTION


NO_PRICE = "ไม่มีราคา"
ESTIMATED_LABEL = "ราคาโดยประมาณ"
CURRENCY = "บาท"

RETAKE_TIPS = (
    "เคล็ดลับการถ่ายรูป:\n"
    "• วางใบวิเคราะห์ให้เรียบ ถ่ายในที่มีแสงสว่างตอนกลางวัน\n"
    "• ถือโทรศัพท์ให้นิ่งและอยู่เหนือกระดาษตรง ๆ\n"
    "• ให้ใบวิเคราะห์เต็มกรอบภาพ\n"
    "• หลีกเลี่ยงเงาและแสงสะท้อน\n"
    "• ดูให้ตัวเลขคมชัด"
)

# Accuracy notices (Requirements 4.2, 22.2, 22.3, 13.5). No word that says the result is checked.
ACCURACY_STARTUP = (
    "หมอดินเอไอ: ความแม่นยำในการอ่านของเอไอยังไม่ได้ทดสอบกับชุดใบวิเคราะห์ดินทดสอบ "
    "ผลที่ได้เป็นเพียงแนวทาง"
)
ACCURACY_CONFIRM = "ค่าเหล่านี้อ่านโดยเอไอ อาจผิดพลาดได้ กรุณาเทียบกับใบวิเคราะห์ของคุณก่อนกดยืนยัน"
ADVICE_NOTICE = "คำแนะนำนี้เป็นแนวทางจากค่าที่คุณยืนยันหรือพิมพ์เข้ามาเท่านั้น"
DEMO_DATA_NOTICE = "ค่าในหน้านี้มาจากข้อมูลสาธิต ไม่ใช่ใบวิเคราะห์จริง"

MENU_HINT = (
    "เลือกปุ่มด้านล่างเพื่อเริ่ม: ส่งรูปใบวิเคราะห์ดิน หรือพิมพ์ค่าดินเอง "
    "(พิมพ์ \"เริ่มใหม่\" ได้ทุกเมื่อ)"
)

AREA_QUESTION = (
    "แปลงของคุณมีขนาดเท่าไร? พิมพ์ได้เลย เช่น \"5\" หรือ \"5 ไร่\" หรือ \"3 ไร่ 2 งาน\" "
    "หรือ \"3 ไร่ 2 งาน 50 ตารางวา\" หรือ \"2 เฮกตาร์\" (ถ้าพิมพ์แค่ตัวเลข จะนับเป็นไร่)"
)
CHOOSE_BUTTON = "กรุณากดปุ่มด้านล่างเพื่อเลือกสิ่งที่ต้องการทำ"
MANUAL_EXAMPLE = "om 1.5 p 20 k 60 ca 800 mg 150 ph 5.8"


def _field(name: str | None) -> str:
    """Label for a field name or a correction target such as rate:0."""
    if not name:
        return ""
    if name in FIELD_LABELS:
        return FIELD_LABELS[name]
    if name.startswith("rate:"):
        return f"อัตราปุ๋ย (กก./ไร่) รายการที่ {int(name.split(':')[1]) + 1}"
    if name.startswith("fertilizer:"):
        return f"ชื่อปุ๋ย รายการที่ {int(name.split(':')[1]) + 1}"
    return name


def _confirm_values(p: Params) -> str:
    lines = [
        "นี่คือค่าที่อ่านได้จากใบวิเคราะห์ดินของคุณ:",
    ]
    origins = p.get("origins", {})
    for name, value in p.get("values", {}).items():
        mark = " (คุณแก้ไข)" if origins.get(name) == "farmer" else ""
        lines.append(f"• {FIELD_LABELS.get(name, name)}: {_num(value)}{mark}")
    lines.append("")
    lines.append("ปุ๋ยที่ใบวิเคราะห์แนะนำ:")
    for it in p.get("items", []):
        mark = " (คุณแก้ไข)" if it.get("origin") == "farmer" else ""
        line = f"{it['index']}. {item_name(it['fertilizer'])} {_num(it['rate_kg_per_rai'])} กก./ไร่{mark}"
        if it.get("rate_warning"):
            line += (
                f"\n   ⚠ อัตรานี้สูงกว่าปกติ (เกิน {_num(p.get('rate_max_kg_per_rai'))} กก./ไร่) "
                "กรุณาตรวจเทียบกับใบวิเคราะห์อีกครั้ง"
            )
        lines.append(line)
    lines.append("")
    lines.append(ACCURACY_CONFIRM)
    return "\n".join(lines)


def _retake(p: Params) -> str:
    names = ", ".join(_field(n) for n in p.get("unreadable", []))
    return (
        f"อ่านส่วนนี้ไม่ได้: {names}\n"
        "กรุณาถ่ายรูปใบวิเคราะห์ดินใหม่ให้ชัดขึ้น ระบบจะไม่เดาค่าที่อ่านไม่ได้\n\n" + RETAKE_TIPS
    )


def _read_failed(p: Params) -> str:
    base = "อ่านรูปไม่สำเร็จ"
    if p.get("attempt", 0) <= 2:
        return base + " กดลองอีกครั้ง หรือพิมพ์ค่าดินเองก็ได้"
    return base + " ลองหลายครั้งแล้ว กรุณาพิมพ์ค่าดินเอง"


def _area_accepted(p: Params) -> str:
    area = _num(p["area_rai"])
    given = str(p.get("input", "")).strip()
    if given in (area, f"{area} ไร่"):
        return f"รับทราบ ขนาดแปลง {area} ไร่"
    return f"รับทราบ {given} = {area} ไร่"


def _area_invalid(p: Params) -> str:
    text = "อ่านขนาดแปลงไม่ได้ กรุณาพิมพ์เป็นตัวเลขมากกว่า 0 พร้อมหน่วย ไร่ งาน ตารางวา ตารางเมตร หรือเฮกตาร์ ตัวอย่าง: " \
           "\"5 ไร่\" หรือ \"3 ไร่ 2 งาน\""
    if p.get("misses", 0) >= 3:
        text += "\nหากไม่สะดวก กดเริ่มใหม่หรือยกเลิกได้"
    return text


def _ask_value(p: Params) -> str:
    target = p.get("target")
    head = f"กรุณาพิมพ์ค่าใหม่ของ {_field(target)}"
    if "textures" in p:
        return head + "\nเลือกจาก: " + ", ".join(p["textures"])
    if "form" in p:
        known = ", ".join(p.get("known", []))
        return head + f"\nรูปแบบ {p['form']} เช่น 46-0-0 หรือชื่อ {known}"
    if "min_exclusive" in p:
        return head + f"\nต้องมากกว่า {_num(p['min_exclusive'])} และไม่เกิน {_num(p['max'])}"
    return head + f"\nช่วงที่รับได้: {_range_text(p)}"


def _correct_invalid(p: Params) -> str:
    return "ค่าที่พิมพ์ใช้ไม่ได้ ค่าเดิมยังไม่เปลี่ยน\n" + _ask_value(p)


def _correct_too_many(p: Params) -> str:
    return "พิมพ์ค่าไม่ถูกต้องหลายครั้ง ระบบคงค่าเดิมไว้ กลับไปที่ปุ่มเลือก"


def _manual_ask(p: Params) -> str:
    lines = ["พิมพ์ค่าดินที่คุณมีได้เลย จะพิมพ์ในข้อความเดียวหรือหลายข้อความก็ได้ ค่าที่รับได้:"]
    for name, rng in p.get("fields", {}).items():
        lines.append(f"• {FIELD_LABELS[name]}: {_num(rng['min'])} ถึง {_num(rng['max'])}")
    lines.append(f"ตัวอย่าง: {MANUAL_EXAMPLE}")
    return "\n".join(lines)


def _manual_accepted(p: Params) -> str:
    lines = ["รับค่าแล้ว:"]
    for name, v in p.get("values", {}).items():
        lines.append(f"• {FIELD_LABELS[name]}: {_num(v)}")
    lines.append("พิมพ์ค่าอื่นเพิ่มได้ หรือกด \"เสร็จแล้ว\" เมื่อพร้อม")
    return "\n".join(lines)


def _manual_invalid(p: Params) -> str:
    if p.get("unrecognized"):
        return f"อ่านค่าที่พิมพ์ไม่ได้ ตัวอย่าง: {MANUAL_EXAMPLE}"
    lines = ["ค่าเหล่านี้อยู่นอกช่วงที่รับได้ ระบบไม่เก็บไว้:"]
    for name, rng in p.get("fields", {}).items():
        lines.append(f"• {FIELD_LABELS[name]}: ต้องอยู่ระหว่าง {_num(rng['min'])} ถึง {_num(rng['max'])}")
    return "\n".join(lines)


def _manual_missing(p: Params) -> str:
    names = ", ".join(_field(n) for n in p.get("missing", []))
    text = f"ยังขาดค่า: {names}\nกรุณาพิมพ์ค่าที่ขาดเพิ่ม"
    if p.get("ph_present"):
        text += " หรือกดขอคำแนะนำจากค่า pH อย่างเดียว"
    return text


def _restarted(p: Params) -> str:
    text = "เริ่มใหม่แล้ว ค่าเดิมถูกล้างหมด"
    if p.get("after_result"):
        text += " (ข้อความเดิมในหน้าแชตยังอยู่)"
    return text


TH: dict[str, Entry] = {
    # replies
    "start.restarted": _restarted,
    "start.notice": ACCURACY_STARTUP,
    "start.menu": MENU_HINT,
    "upload.received": "ได้รับรูปแล้ว กำลังอ่านค่า รอสักครู่",
    "upload.ask": "กรุณาส่งรูปถ่ายใบวิเคราะห์ดิน (ไฟล์ JPEG หรือ PNG)",
    "upload.too_large": "รูปมีขนาดใหญ่เกินไป (เกิน 10 MB) กรุณาส่งรูปที่เล็กลง",
    "upload.retrying": "กำลังลองอ่านรูปอีกครั้ง รอสักครู่",
    "read.failed": _read_failed,
    "read.not_dld": "รูปนี้ดูไม่ใช่ใบวิเคราะห์ดินของกรมพัฒนาที่ดิน กรุณาส่งรูปใบวิเคราะห์ดินหรือพิมพ์ค่าดินเอง",
    "retake.message": _retake,
    "confirm.values": _confirm_values,
    "correct.ask_target": "ต้องการแก้ค่าไหน? กดปุ่มด้านล่าง หรือพิมพ์ชื่อค่า เช่น ph, k, rate1",
    "correct.target_invalid": "ไม่พบค่าที่ต้องการแก้ กรุณากดปุ่มเลือกค่าที่ต้องการแก้",
    "correct.ask_value": _ask_value,
    "correct.invalid": _correct_invalid,
    "correct.too_many": _correct_too_many,
    "area.ask": AREA_QUESTION,
    "area.accepted": _area_accepted,
    "area.invalid": _area_invalid,
    "cancel.done": "ยกเลิกแล้ว ยังไม่ได้คำนวณอะไร ค่าทั้งหมดถูกล้างแล้ว กดเริ่มใหม่เมื่อพร้อม",
    "result.next_steps": "ต้องการดูผลของขนาดแปลงอื่น หรือเริ่มใหม่ไหม?",
    "session.cancelled_start_again": "รายการนี้ถูกยกเลิกแล้ว กรุณากดเริ่มใหม่",
    "error.generic": "ขออภัย ระบบขัดข้อง กรุณากดเริ่มใหม่",
    "error.advice_failed": "ขออภัย สร้างคำแนะนำไม่สำเร็จ กรุณากดเริ่มใหม่",
    "input.choose_button": CHOOSE_BUTTON,
    "manual.ask": _manual_ask,
    "manual.accepted": _manual_accepted,
    "manual.invalid": _manual_invalid,
    "manual.missing": _manual_missing,
    "manual.too_many": "พิมพ์ค่าไม่ถูกต้องหลายครั้ง ค่าที่รับแล้วยังอยู่ กดปุ่มด้านล่างเพื่อไปต่อ",
    "manual.nothing_yet": "ยังไม่มีค่าที่รับไว้ กรุณาพิมพ์ค่าดินอย่างน้อยหนึ่งค่า",
    # button labels
    "button.restart": "เริ่มใหม่",
    "button.cancel": "ยกเลิก",
    "button.upload_sheet": "ส่งรูปใบวิเคราะห์ดิน",
    "button.manual_entry": "พิมพ์ค่าดินเอง",
    "button.confirm": "ยืนยัน",
    "button.correct": "แก้ไข",
    "button.retry": "ลองอ่านอีกครั้ง",
    "button.done": "เสร็จแล้ว",
    "button.ph_only": "ขอคำแนะนำจากค่า pH อย่างเดียว",
    "button.change_area": "เปลี่ยนขนาดแปลง",
    "target.rate": lambda p: f"อัตราปุ๋ย รายการที่ {p.get('index', '')}",
    "target.fertilizer": lambda p: f"ชื่อปุ๋ย รายการที่ {p.get('index', '')}",
    **{f"target.{n}": label for n, label in FIELD_LABELS.items() if n != "sheet_recommendations"},
}


def text_for(key: str, params: Params | None = None) -> str:
    """Thai text for a key. Raises KeyError for an unknown key so a gap is never hidden."""
    entry = TH[key]
    return entry(params or {}) if callable(entry) else entry


def _render_button(b: ButtonSpec) -> dict[str, Any]:
    return {"label": text_for(b.label_key, b.params), "action": b.action, "payload": b.payload}


SCRIPT_HEADING = "ประโยคสำหรับบอกร้านปุ๋ย:"
GUIDE_HEADING = "ถ้าใช้ทีละไร่:"


def render_advice(advice: Any) -> list[dict[str, Any]]:
    """Bubbles for an AdviceMessage: demo label, table, explanation, shop script, notices."""
    bubbles: list[dict[str, Any]] = []
    if advice.demo_label:
        bubbles.append({"kind": "text", "text": advice.demo_label, "buttons": []})
    t = advice.table
    bubbles.append(
        {
            "kind": "table",
            "text": t.text_version,
            "buttons": [],
            "table": {
                "heading": t.heading,
                "columns": list(t.columns),
                "rows": [list(r) for r in t.rows],
                "total_row": list(t.total_row),
            },
        }
    )
    ph_summary = getattr(advice, "ph_summary", None)
    if ph_summary:
        # Comes before the table. The plain text keeps the same words for renderers
        # that do not draw cards.
        bubbles.insert(
            0 if not advice.demo_label else 1,
            {
                "kind": "ph_summary",
                "text": "\n".join(
                    [
                        f"{ph_summary['title']}: pH {ph_summary['ph']} {ph_summary['headline']}",
                        ph_summary["range"],
                        ph_summary["advice"],
                        ph_summary["lab"],
                    ]
                ),
                "buttons": [],
                "card": ph_summary,
            },
        )
    parts = [advice.soil_summary]
    if advice.per_rai_guide:
        parts.append(GUIDE_HEADING + "\n" + "\n".join(advice.per_rai_guide))
    parts.append(advice.expected_effect)
    bubbles.append(
        {
            "kind": "advice",
            "text": "\n\n".join(parts),
            "buttons": [],
            "sections": {
                "summary_title": ADVICE_SUMMARY_TITLE,
                "summary": advice.soil_summary,
                "summary_in_ph_card": bool(ph_summary),
                "guide_title": ADVICE_GUIDE_TITLE,
                "guide": list(advice.per_rai_guide),
                "effect_title": ADVICE_EFFECT_TITLE,
                "effect": advice.expected_effect,
            },
        }
    )
    bubbles.append(
        {"kind": "text", "text": SCRIPT_HEADING + "\n" + " ".join(advice.shop_script), "buttons": []}
    )
    if advice.notices:
        bubbles.append(
            {
                "kind": "text",
                "text": "\n".join(advice.notices),
                "buttons": [],
                "notices": [n for n in advice.notices if not (ph_summary and n == ph_summary["lab"])],
                "notices_title": NOTICES_TITLE,
            }
        )
    return bubbles


ADVICE_SUMMARY_TITLE = "สภาพดิน"
ADVICE_GUIDE_TITLE = "ถ้าใช้ทีละไร่"
ADVICE_EFFECT_TITLE = "ผลที่น่าจะได้"
NOTICES_TITLE = "ข้อควรรู้"


def render(reply: Reply) -> dict[str, Any]:
    """Turn a reply spec into a bubble: {kind, text, buttons}."""
    buttons = [_render_button(b) for b in reply.buttons]
    bubble: dict[str, Any] = {
        "kind": "buttons" if buttons else "text",
        "text": text_for(reply.key, reply.params),
        "buttons": buttons,
    }
    if reply.key == "confirm.values":
        bubble["card"] = _confirm_card(reply.params)
    return bubble


CONFIRM_CARD_TITLE = "ค่าที่อ่านได้จากใบวิเคราะห์ดิน"
CONFIRM_CARD_SUBTITLE = "อ่านโดยเอไอ · ตรวจทานก่อนใช้"
CONFIRM_CARD_ITEMS = "ปุ๋ยที่ใบวิเคราะห์แนะนำ"
CONFIRM_CARD_QUESTION = "ค่าที่อ่านได้ถูกต้องไหมครับ?"
EDITED_MARK = "คุณแก้ไข"


def _confirm_card(p: Params) -> dict[str, Any]:
    """Structured form of the confirm message, for pages that draw value tiles.

    Display only: the values and rates are the ones in the params, formatted, never changed.
    """
    origins = p.get("origins", {})
    fields = [
        {
            "name": name,
            "label": FIELD_LABELS.get(name, name),
            "value": _num(value),
            "edited": origins.get(name) == "farmer",
        }
        for name, value in p.get("values", {}).items()
    ]
    items = [
        {
            "name": item_name(it["fertilizer"]),
            "rate": f"{_num(it['rate_kg_per_rai'])} กก./ไร่",
            "edited": it.get("origin") == "farmer",
            "warning": (
                f"อัตรานี้สูงกว่าปกติ (เกิน {_num(p.get('rate_max_kg_per_rai'))} กก./ไร่) "
                "กรุณาตรวจเทียบกับใบวิเคราะห์อีกครั้ง"
                if it.get("rate_warning")
                else ""
            ),
        }
        for it in p.get("items", [])
    ]
    return {
        "type": "confirm_values",
        "title": CONFIRM_CARD_TITLE,
        "subtitle": CONFIRM_CARD_SUBTITLE,
        "fields": fields,
        "items_title": CONFIRM_CARD_ITEMS,
        "items": items,
        "edited_mark": EDITED_MARK,
        "question": CONFIRM_CARD_QUESTION,
        "note": ACCURACY_CONFIRM,
    }
