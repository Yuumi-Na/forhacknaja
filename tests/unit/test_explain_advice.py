import re
from decimal import Decimal

from mordin.data import load_data
from mordin.explain import templates
from mordin.explain.advice import build_advice
from mordin.explain.script import template_script
from mordin.fertilizer.amendments import build_ph_plan
from mordin.fertilizer.sheet_plan import build_sheet_plan
from mordin.flows.session import Session

DATA = load_data()
FORBIDDEN = ("รับรอง", "รับประกัน", "แน่นอน", "ตรวจสอบแล้ว", "verified", "guarantee")


def _sheet_plan(recs, area=5):
    return build_sheet_plan(recs, area, DATA.prices, DATA.limits)


def _all_text(msg, include_label=False):
    parts = [msg.soil_summary, msg.expected_effect, *msg.shop_script, *msg.per_rai_guide, *msg.notices]
    if include_label and msg.demo_label:
        parts.append(msg.demo_label)
    return "\n".join(parts)


def test_per_rai_guide_matches_requirement_example():
    plan = _sheet_plan([{"fertilizer": "urea", "rate_kg_per_rai": "20.98"}])
    line = templates.per_rai_line(plan.items[0], Decimal(5))
    assert "ถ้าปุ๋ยถุงละ 5 กก. ใช้หว่านประมาณ 4 ถุงต่อ 1 ไร่ (ประมาณ 20.98 กก.)" in line


def test_per_rai_guide_half_bag_and_less_than_half():
    plan = _sheet_plan(
        [{"fertilizer": "urea", "rate_kg_per_rai": 12}, {"fertilizer": "dap", "rate_kg_per_rai": 1}]
    )
    assert "ประมาณ 2.5 ถุงต่อ 1 ไร่" in templates.per_rai_line(plan.items[0], Decimal(5))
    low = templates.per_rai_line(plan.items[1], Decimal(5))
    assert "น้อยกว่าครึ่งถุงต่อ 1 ไร่" in low and "0 ถุง" not in low


def test_script_at_most_3_sentences_for_any_item_count_and_has_figures_no_bags():
    for n in (0, 1, 2, 5, 9):
        recs = [{"fertilizer": "urea", "rate_kg_per_rai": 20 + i} for i in range(n)]
        plan = _sheet_plan(recs, "3.5")
        script = template_script(plan)
        assert 1 <= len(script) <= 3
        text = " ".join(script)
        assert "3.5" in text
        for item in plan.items:
            assert f"{item.script_kg} กิโล" in text
        assert "ถุง" not in text


def test_sheet_advice_uses_plan_values_and_statuses():
    fx = {"om": 1.0, "p": 5.0, "k": 20.0, "ph": 5.5}
    session = Session(values=fx)
    plan = _sheet_plan([{"fertilizer": "urea", "rate_kg_per_rai": "20.98"}])
    msg = build_advice(plan, session, DATA)
    assert msg.demo_label is None
    assert msg.table.heading.endswith("ไร่") and "5" in msg.table.heading
    assert len(msg.per_rai_guide) == 1
    assert msg.soil_summary.count("•") == len(
        [k for k in fx if k in templates.SOIL_NAMES]
    )
    assert any("ราคาโดยประมาณ" in n and "01-01-2025" in n for n in msg.notices)
    assert any("ใบวิเคราะห์" in n for n in msg.notices)


def test_expectation_wording_without_promise_or_numbers():
    plan = _sheet_plan([{"fertilizer": "urea", "rate_kg_per_rai": 20}])
    msg = build_advice(plan, Session(values={"om": 1.0}), DATA)
    assert "น่าจะ" in msg.expected_effect
    assert not re.search(r"\d", msg.expected_effect)
    text = _all_text(msg)
    assert not any(w in text for w in FORBIDDEN)


def test_ph_only_acidic_has_label_first_step_and_lab_test():
    plan = build_ph_plan(5.5, 2, DATA.amendments, DATA.prices, DATA.limits)
    msg = build_advice(plan, Session(values={"ph": 5.5}), DATA)
    assert msg.demo_label == DATA.amendments["label"]
    assert "เป็นกรด" in msg.soil_summary
    assert any("ขั้นแรก" in n and "ตรวจดิน" in n for n in msg.notices)
    assert len(msg.per_rai_guide) == len(plan.items) == 2
    assert all("วัสดุ" in g for g in msg.per_rai_guide)
    assert not any(w in _all_text(msg) for w in FORBIDDEN)


def test_ph_only_balanced_says_no_material_and_shows_no_amount():
    plan = build_ph_plan(6.2, 2, DATA.amendments, DATA.prices, DATA.limits)
    msg = build_advice(plan, Session(values={"ph": 6.2}), DATA)
    assert "ไม่ต้องใส่วัสดุ" in msg.soil_summary
    assert msg.per_rai_guide == ()
    assert 1 <= len(msg.shop_script) <= 3
    assert any("ตรวจดิน" in n for n in msg.notices)


def test_ph_only_alkaline_no_material_advisable():
    plan = build_ph_plan(7.5, 2, DATA.amendments, DATA.prices, DATA.limits)
    msg = build_advice(plan, Session(values={"ph": 7.5}), DATA)
    assert "แนะนำวัสดุปรับปรุงดินให้ไม่ได้" in msg.soil_summary


def test_basic_formula_plan_shows_rules_label_and_stub_notice():
    plan = _sheet_plan([{"fertilizer": "urea", "rate_kg_per_rai": 20}])
    plan = type(plan)(
        source="basic_formula",
        area_rai=plan.area_rai,
        items=plan.items,
        price_date=plan.price_date,
        uses_demo_rules=True,
        soil_status={"om": "low", "k": "good"},
    )
    msg = build_advice(plan, Session(), DATA, stub=True)
    assert msg.demo_label == DATA.basic_formula["label"]
    assert "อินทรียวัตถุในดิน: ต่ำ" in msg.soil_summary
    assert msg.soil_summary.count("•") == 2
    assert any("ข้อมูลสาธิต" in n for n in msg.notices)


def test_ph_only_advice_has_ph_summary_card():
    plan = build_ph_plan(5.8, 5, DATA.amendments, DATA.prices, DATA.limits)
    msg = build_advice(plan, Session(values={"ph": 5.8}), DATA)
    card = msg.ph_summary
    assert card["ph"] == "5.8" and card["ph_class"] == "acidic"
    assert card["range"].endswith("pH 6.0-6.5")
    assert card["advice"] == msg.soil_summary
    assert card["lab"] == templates.PH_FIRST_STEP


def test_ph_summary_only_on_ph_only_path():
    plan = _sheet_plan([{"fertilizer": "46-0-0", "rate_kg_per_rai": 20.98}])
    assert build_advice(plan, Session(values={"ph": 5.8}), DATA).ph_summary is None


def test_render_advice_puts_ph_card_before_table_and_keeps_everything():
    from mordin.explain.messages import render_advice

    plan = build_ph_plan(5.8, 5, DATA.amendments, DATA.prices, DATA.limits)
    msg = build_advice(plan, Session(values={"ph": 5.8}), DATA)
    kinds = [b["kind"] for b in render_advice(msg)]
    assert kinds.index("ph_summary") < kinds.index("table") < kinds.index("advice")
    adv = next(b for b in render_advice(msg) if b["kind"] == "advice")
    assert adv["sections"]["guide"] == list(msg.per_rai_guide)
    assert adv["sections"]["summary_in_ph_card"] is True
