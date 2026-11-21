import logging
import time

from mordin.data import load_data
from mordin.explain import templates
from mordin.explain.advice import AdviceText, build_advice
from mordin.explain.figures import check_figures, check_wording
from mordin.explain.script import ScriptDraft, check_script, template_script
from mordin.fertilizer.sheet_plan import build_sheet_plan
from mordin.flows.session import Session

DATA = load_data()
PLAN = build_sheet_plan(
    [{"fertilizer": "urea", "rate_kg_per_rai": "20.98"}], 5, DATA.prices, DATA.limits
)
GOOD_SCRIPT = ["ผมมีแปลงอ้อย 5 ไร่", "ต้องการยูเรีย ประมาณ 105 กิโล", "ช่วยแนะนำให้หน่อย"]
SESSION = Session(values={"om": 1.0})


def _text(script=None, summary="ดินของคุณขาดอาหารบางอย่าง", effect="น่าจะช่วยให้อ้อยโตดีขึ้น"):
    return AdviceText(soil_summary=summary, expected_effect=effect, shop_script=script or GOOD_SCRIPT)


def _build(caller, deadline=10.0):
    return build_advice(PLAN, SESSION, DATA, model_caller=caller, deadline=deadline)


def test_check_figures_flags_units_not_allowed_and_accepts_allowed():
    assert check_figures("ใช้ 20 กก. ราคา 100 บาท") == ["20 กก.", "100 บาท"]
    assert check_figures("พื้นที่ 5 ไร่", {"area": [5]}) == []
    assert check_figures("ใช้ 3 ถุง", {"weight": [3]}) == ["3 ถุง"]
    assert check_figures("ดินมี pH ต่ำ ระดับ 5.5") == []


def test_check_wording_flags_promise_and_yield_numbers():
    assert check_wording("ผ่านการตรวจสอบแล้ว") == ["ตรวจสอบแล้ว"]
    assert check_wording("ผลผลิตเพิ่ม 20") == ["yield_number"]
    assert check_wording("น่าจะช่วยให้อ้อยโต") == []


def test_check_script_accepts_good_and_rejects_each_problem():
    ok = ScriptDraft(sentences=GOOD_SCRIPT)
    assert check_script(ok, PLAN) == []
    assert "missing_script_kg:urea" in check_script(ScriptDraft(sentences=["ผมมี 5 ไร่"]), PLAN)
    assert "missing_area_rai" in check_script(ScriptDraft(sentences=["ยูเรีย 105 กิโล"]), PLAN)
    assert "bag_figure" in check_script(ScriptDraft(sentences=[*GOOD_SCRIPT[:2], "เอา 4 ถุง"]), PLAN)
    assert "extra_figure" in check_script(ScriptDraft(sentences=[*GOOD_SCRIPT[:2], "ราคา 900 บาท"]), PLAN)


def test_script_draft_limits_to_three_sentences_and_template_passes_check():
    try:
        ScriptDraft(sentences=["a", "b", "c", "d"])
        raised = False
    except ValueError:
        raised = True
    assert raised
    assert check_script(ScriptDraft(sentences=template_script(PLAN)), PLAN) == []


def test_good_model_text_is_used():
    msg = _build(lambda _t: _text())
    assert msg.shop_script == tuple(GOOD_SCRIPT)
    assert msg.soil_summary == "ดินของคุณขาดอาหารบางอย่าง"
    assert msg.expected_effect == "น่าจะช่วยให้อ้อยโตดีขึ้น"


def test_bad_blocks_fall_back_per_block():
    bad = _text(summary="มี 20 กก.", effect="รับประกันผล", script=GOOD_SCRIPT)
    msg = _build(lambda _t: bad)
    assert msg.shop_script == tuple(GOOD_SCRIPT)
    plain = build_advice(PLAN, SESSION, DATA)
    assert msg.soil_summary == plain.soil_summary
    assert msg.expected_effect == plain.expected_effect


def test_bad_script_retries_once_and_uses_second_answer():
    calls = []

    def caller(text):
        calls.append(text)
        return _text(script=["ผมมี 5 ไร่ ต้องการ 4 ถุง"]) if len(calls) == 1 else _text()

    msg = _build(caller)
    assert len(calls) == 2 and "rejected" in calls[1]
    assert msg.shop_script == tuple(GOOD_SCRIPT)


def test_two_bad_scripts_use_template_script_without_third_call():
    calls = []

    def caller(text):
        calls.append(text)
        return _text(script=["ราคา 900 บาท"])

    msg = _build(caller)
    assert len(calls) == 2
    assert msg.shop_script == tuple(template_script(PLAN))
    assert msg.expected_effect == "น่าจะช่วยให้อ้อยโตดีขึ้น"


def test_model_error_uses_all_templates_with_one_log(caplog):
    def caller(_t):
        raise RuntimeError("boom")

    with caplog.at_level(logging.WARNING, logger="mordin.explain"):
        msg = _build(caller)
    assert len([r for r in caplog.records if r.name == "mordin.explain"]) == 1
    assert msg.shop_script == tuple(template_script(PLAN))
    assert msg.expected_effect == templates.expected_effect_text(PLAN)


def test_timeout_uses_all_templates_with_one_log(caplog):
    def caller(_t):
        time.sleep(0.5)
        return _text()

    with caplog.at_level(logging.WARNING, logger="mordin.explain"):
        msg = _build(caller, deadline=0.05)
    assert len([r for r in caplog.records if r.name == "mordin.explain"]) == 1
    assert msg.shop_script == tuple(template_script(PLAN))
