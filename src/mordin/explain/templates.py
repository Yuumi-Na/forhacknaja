"""Fixed Thai templates for the advice blocks. No arithmetic: figures come from the Plan.

Used as the template Explainer (Req 13) and as the fallback when a model-written block is
rejected (task 6.4). Nothing here says the result is checked or promises a yield.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Mapping

from mordin.explain import messages
from mordin.fertilizer.plan import Plan, PlanItem

# Soil value order and short plain names (no chemical symbol without a plain word).
SOIL_ORDER: tuple[str, ...] = ("om", "p", "k", "ca", "mg", "ph", "soil_texture")
SOIL_NAMES: dict[str, str] = {
    "om": "อินทรียวัตถุในดิน",
    "p": "ฟอสฟอรัส (ธาตุช่วยให้รากและการแตกกอดี)",
    "k": "โพแทสเซียม (ธาตุช่วยให้อ้อยสะสมน้ำตาล)",
    "ca": "แคลเซียม",
    "mg": "แมกนีเซียม",
    "ph": "ความเป็นกรดด่างของดิน (pH)",
    "soil_texture": "เนื้อดิน",
}
STATUS_WORDS: dict[str, str] = {
    "good": "ดี",
    "fair": "พอใช้",
    "low": "ต่ำ",
    "needs_action": "ควรปรับปรุง",
}

SOIL_SUMMARY_HEAD = "สภาพดินของคุณจากค่าที่ได้รับ:"
SOIL_SUMMARY_NONE = "ยังไม่มีค่าดินที่ใช้สรุปสภาพดินได้"

PH_CLASS_TEXT: dict[str, str] = {
    "acidic": "ดินของคุณค่อนข้างเป็นกรด ซึ่งต่ำกว่าที่อ้อยชอบ",
    "balanced": "ดินของคุณมีความเป็นกรดด่างอยู่ในระดับที่เหมาะกับอ้อย",
    "alkaline": "ดินของคุณค่อนข้างเป็นด่าง ซึ่งสูงกว่าที่อ้อยชอบ",
}
# pH summary card (pH-only path). Headlines name the class only: there are no sub-bands
# such as "slightly acidic" in soil_amendments.json, so none are claimed.
PH_CARD_TITLE = "ผลวิเคราะห์ดิน"
PH_CARD_SUBTITLE = "จากค่า pH"
PH_CARD_HEADLINE: dict[str, str] = {
    "acidic": "ดินเป็นกรด",
    "balanced": "ดินเป็นกลาง เหมาะกับอ้อย",
    "alkaline": "ดินเป็นด่าง",
}
PH_CARD_ADVICE_TITLE = "คำแนะนำ"
PH_CARD_LAB_TITLE = "ตรวจดินเพิ่มเติม"


def ph_range_text(lower: str, upper: str) -> str:
    return f"ช่วงที่เหมาะกับอ้อย: pH {lower}-{upper}"


NO_MATERIAL_BALANCED = "ตอนนี้ยังไม่ต้องใส่วัสดุปรับปรุงดิน"
NO_MATERIAL_ADVISABLE = "ตอนนี้ยังแนะนำวัสดุปรับปรุงดินให้ไม่ได้"
PH_FIRST_STEP = (
    "นี่เป็นเพียงขั้นแรกจากค่า pH อย่างเดียวเท่านั้น "
    "ควรส่งตรวจดินที่ห้องปฏิบัติการเพื่อให้ได้คำแนะนำที่ละเอียดขึ้น"
)

EFFECT_FERTILIZER = (
    "ถ้าใส่ปุ๋ยตามคำแนะนำนี้ น่าจะช่วยให้อ้อยได้อาหารพอดีกับดินของคุณ "
    "และน่าจะช่วยให้อ้อยเจริญเติบโตดีขึ้น ผลที่ได้จริงยังขึ้นกับฝน น้ำ และการดูแลแปลงด้วย"
)
EFFECT_AMENDMENT_ACIDIC = (
    "ถ้าใส่วัสดุปรับปรุงดินตามคำแนะนำนี้ ดินน่าจะเป็นกรดน้อยลง "
    "และน่าจะช่วยให้อ้อยดูดอาหารจากดินได้ดีขึ้น ผลที่ได้จริงยังขึ้นกับฝน น้ำ และการดูแลแปลงด้วย"
)
EFFECT_AMENDMENT_NONE = (
    "เมื่อยังไม่มีวัสดุที่แนะนำให้ใส่ในตอนนี้ การตรวจดินที่ห้องปฏิบัติการ "
    "น่าจะช่วยให้วางแผนดูแลแปลงอ้อยได้ดีขึ้น"
)

DEMO_RULES_NOTICE_PREFIX = "สถานะดินด้านบนใช้เกณฑ์ตัวอย่างสำหรับสาธิต: "
PRICE_NOTICE = (
    "ราคาทุกรายการเป็น{estimated} หน่วยเป็นบาท ตามข้อมูลวันที่ {date} "
    "ราคาที่ร้านจริงอาจไม่เท่ากัน"
)
SOURCE_NOTICE_SHEET = "ปริมาณต่อไร่มาจากสูตรและอัตราที่ใบวิเคราะห์ดินแนะนำ ระบบไม่ได้คำนวณใหม่"

SCRIPT_AREA = "ผมมีแปลงอ้อยขนาด {area} ไร่"
SCRIPT_ITEMS = "ต้องการ{items}"
SCRIPT_ITEM = "{name} ประมาณ {kg} กิโล"
SCRIPT_NONE = "ตอนนี้ยังไม่ต้องซื้อวัสดุปรับปรุงดิน"
SCRIPT_ASK = "ช่วยแนะนำสินค้าให้หน่อย"


def fmt_decimal(value: Decimal) -> str:
    """Fixed-point text with the Decimal's own decimal places (same as the table)."""
    return format(value, "f")


def _fmt_bags(value: Decimal) -> str:
    text = format(value, "f")
    return text.rstrip("0").rstrip(".") if "." in text else text


def format_price_date(iso: str) -> str:
    """Day-month-year text, e.g. 2025-01-01 -> 01-01-2025. An unparsable date is shown as is."""
    try:
        d = date.fromisoformat(iso)
    except ValueError:
        return iso
    return f"{d.day:02d}-{d.month:02d}-{d.year}"


def soil_summary_text(plan: Plan, statuses: Mapping[str, str]) -> str:
    """Soil summary. One status per value for sheet and basic plans, the pH class for pH-only."""
    if plan.source == "ph_only":
        lines = [PH_CLASS_TEXT.get(plan.ph_class or "", "")]
        if not plan.items:
            lines.append(NO_MATERIAL_BALANCED if plan.ph_class == "balanced" else NO_MATERIAL_ADVISABLE)
        return "\n".join(line for line in lines if line)
    lines = [SOIL_SUMMARY_HEAD]
    found = False
    for name in SOIL_ORDER:
        status = statuses.get(name)
        if status in STATUS_WORDS:
            lines.append(f"• {SOIL_NAMES[name]}: {STATUS_WORDS[status]}")
            found = True
    if not found:
        return SOIL_SUMMARY_NONE
    return "\n".join(lines)


def expected_effect_text(plan: Plan) -> str:
    """Expectation wording only. No yield number, no promise."""
    if plan.source == "ph_only":
        if not plan.items:
            return EFFECT_AMENDMENT_NONE
        return EFFECT_AMENDMENT_ACIDIC if plan.ph_class == "acidic" else EFFECT_FERTILIZER
    return EFFECT_FERTILIZER


def per_rai_line(item: PlanItem, small_bag_kg: Decimal, *, material: bool = False) -> str:
    """Per 1 rai guide from rate_small_bags_per_rai and rate_kg_per_rai (Req 13.11)."""
    kind = "วัสดุ" if material else "ปุ๋ย"
    bag_kg = _fmt_bags(small_bag_kg)
    kg = fmt_decimal(item.rate_kg_per_rai)
    if item.rate_small_bags_per_rai == 0:
        amount = "น้อยกว่าครึ่งถุง"
    else:
        amount = f"{_fmt_bags(item.rate_small_bags_per_rai)} ถุง"
    return (
        f"{messages.item_name(item.key)}: ถ้า{kind}ถุงละ {bag_kg} กก. "
        f"ใช้หว่านประมาณ {amount}ต่อ 1 ไร่ (ประมาณ {kg} กก.)"
    )


def notices_for(plan: Plan, *, stub: bool = False, rules_label: str | None = None) -> tuple[str, ...]:
    """Guide notice, price note with date, source notes and the pH-only first-step notice."""
    out = [messages.ADVICE_NOTICE]
    out.append(
        PRICE_NOTICE.format(
            estimated=messages.ESTIMATED_LABEL, date=format_price_date(plan.price_date)
        )
    )
    if plan.source == "sheet":
        out.append(SOURCE_NOTICE_SHEET)
        if rules_label:
            out.append(DEMO_RULES_NOTICE_PREFIX + rules_label)
    if plan.source == "ph_only":
        out.append(PH_FIRST_STEP)
    if stub:
        out.append(messages.DEMO_DATA_NOTICE)
    return tuple(out)
