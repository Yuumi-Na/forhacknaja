from decimal import Decimal

import pytest

from mordin.data import load_data
from mordin.flows import (
    BuildAdvice,
    Button,
    Explained,
    ExplainFailed,
    ImageUploaded,
    ReadFailed,
    ReadImage,
    ReadSucceeded,
    Session,
    SheetItem,
    State,
    Text,
    reduce,
)

DATA = load_data()
GOOD_VALUES = {"om": 1.2, "p": 8.0, "k": 60.0, "ca": 400.0, "mg": 70.0, "ph": 5.4,
               "soil_texture": "ร่วนทราย"}


def good_read(rate="50", **over):
    return ReadSucceeded(
        values={**GOOD_VALUES, **over},
        sheet_recommendations=[SheetItem(fertilizer="15-15-15", rate_kg_per_rai=Decimal(rate))],
    )


def run(session, *events):
    """Feed events one by one. Return the last step and all steps."""
    steps = []
    for ev in events:
        step = reduce(session, ev, DATA)
        session = step.session
        steps.append(step)
    return steps[-1], steps


def keys(step):
    return [r.key for r in step.replies]


def at_confirm(rate="50"):
    step, _ = run(Session(), ImageUploaded("a.jpg"), good_read(rate))
    return step


def at_area_question():
    step, _ = run(at_confirm().session, Button("confirm"))
    return step


def at_result():
    step, _ = run(at_area_question().session, Text("5"), Explained(advice=None))
    return step


# --- upload and read ---
def test_upload_accepted_requests_read():
    step = reduce(Session(), ImageUploaded("a.jpg"), DATA)
    assert keys(step) == ["upload.received"]
    assert step.commands == [ReadImage("a.jpg")]
    assert step.session.state == State.IMAGE_RECEIVED
    assert step.session.source == "lab_sheet"


def test_read_ok_goes_to_confirm_with_three_buttons():
    step = at_confirm()
    assert step.session.state == State.VALUES_READ
    assert step.replies[0].key == "confirm.values"
    assert [b.action for b in step.replies[0].buttons] == ["confirm", "correct", "cancel"]
    assert step.session.value_origin["ph"] == "read"
    assert step.commands == []


def test_read_failed_allows_two_retries_then_manual_only():
    s = reduce(Session(), ImageUploaded("a.jpg"), DATA).session
    s1 = reduce(s, ReadFailed("timeout"), DATA)
    assert "retry_read" in [b.action for b in s1.replies[0].buttons]
    s2 = reduce(s1.session, ReadFailed(), DATA)
    assert "retry_read" in [b.action for b in s2.replies[0].buttons]
    s3 = reduce(s2.session, ReadFailed(), DATA)
    assert [b.action for b in s3.replies[0].buttons] == ["manual_entry"]
    assert s3.session.state == State.IMAGE_RECEIVED
    # no retry once the limit is passed
    again = reduce(s3.session, Button("retry_read"), DATA)
    assert again.commands == []


def test_retry_read_rereads_same_image():
    s = reduce(Session(), ImageUploaded("a.jpg"), DATA).session
    s = reduce(s, ReadFailed(), DATA).session
    step = reduce(s, Button("retry_read"), DATA)
    assert step.commands == [ReadImage("a.jpg")]


def test_unreadable_fields_named_and_no_values_kept():
    s = reduce(Session(), ImageUploaded("a.jpg"), DATA).session
    ev = ReadSucceeded(
        values={**GOOD_VALUES, "k": None},
        sheet_recommendations=[],
        unreadable={"k": "blurry"},
    )
    step = reduce(s, ev, DATA)
    assert step.session.state == State.RETAKE_NEEDED
    reply = step.replies[0]
    assert reply.key == "retake.message"
    assert reply.params["unreadable"] == ["k", "sheet_recommendations"]
    assert reply.params["reasons"]["k"] == "blurry"
    assert [b.action for b in reply.buttons] == ["upload_sheet"]
    assert step.session.values == {} and step.session.sheet_recommendations == []
    assert step.commands == []


def test_out_of_range_value_is_treated_as_unreadable():
    s = reduce(Session(), ImageUploaded("a.jpg"), DATA).session
    step = reduce(s, good_read(ph=99.0), DATA)
    assert step.session.state == State.RETAKE_NEEDED
    assert "ph" in step.replies[0].params["unreadable"]


def test_manual_button_after_two_unreadable_reads_in_a_row():
    bad = ReadSucceeded(values={}, sheet_recommendations=[])
    _, steps = run(Session(), ImageUploaded("a"), bad, ImageUploaded("b"), bad)
    assert [b.action for b in steps[1].replies[0].buttons] == ["upload_sheet"]
    assert [b.action for b in steps[3].replies[0].buttons] == ["upload_sheet", "manual_entry"]
    # a good retake resets the count and discards the earlier reading
    ok, _ = run(steps[3].session, ImageUploaded("c"), good_read())
    assert ok.session.state == State.VALUES_READ
    assert ok.session.reads_failed_in_a_row == 0


def test_not_dld_sheet_reply_discards_values():
    s = reduce(Session(), ImageUploaded("a.jpg"), DATA).session
    step = reduce(s, ReadSucceeded(values=dict(GOOD_VALUES), is_dld_sheet=False), DATA)
    assert keys(step) == ["read.not_dld"]
    assert [b.action for b in step.replies[0].buttons] == ["upload_sheet", "manual_entry"]
    assert step.session.values == {}
    assert step.commands == []


# --- confirm and correct ---
def test_rate_warning_only_for_positive_rate_above_max():
    items = at_confirm(rate="250").replies[0].params["items"]
    assert items[0]["rate_warning"] is True
    assert at_confirm(rate="200").replies[0].params["items"][0]["rate_warning"] is False
    assert at_confirm(rate="50").replies[0].params["items"][0]["rate_warning"] is False


def test_correct_value_one_at_a_time_records_farmer_origin():
    step, _ = run(at_confirm().session, Button("correct"), Text("ph"), Text("6.1"))
    assert step.session.values["ph"] == 6.1
    assert step.session.value_origin["ph"] == "farmer"
    assert step.session.value_origin["k"] == "read"
    assert step.replies[0].key == "confirm.values"
    assert step.session.pending is None


def test_correct_rate_and_fertilizer_of_item():
    step, _ = run(
        at_confirm().session,
        Button("correct"), Text("rate"), Text("60"),
        Button("correct"), Button("correct_target", "fertilizer:0"), Text("46-0-0"),
    )
    item = step.session.sheet_recommendations[0]
    assert item.rate_kg_per_rai == Decimal("60")
    assert item.fertilizer == "46-0-0"
    assert item.origin == "farmer"


def test_invalid_correction_keeps_value_and_asks_again():
    step, steps = run(at_confirm().session, Button("correct"), Text("ph"), Text("42"))
    assert step.replies[0].key == "correct.invalid"
    assert step.replies[0].params["max"] == 10.0
    assert step.session.values["ph"] == 5.4


def test_three_invalid_corrections_return_to_confirm_buttons():
    step, _ = run(at_confirm().session, Button("correct"), Text("ph"),
                  Text("x"), Text("42"), Text("-1"))
    assert keys(step) == ["correct.too_many", "confirm.values"]
    assert step.session.values["ph"] == 5.4
    assert step.session.pending is None
    assert [b.action for b in step.replies[1].buttons] == ["confirm", "correct", "cancel"]


def test_rate_correction_must_be_positive_and_within_max():
    base, _ = run(at_confirm().session, Button("correct"), Text("rate"))
    for bad in ("0", "201", "abc"):
        step = reduce(base.session, Text(bad), DATA)
        assert step.replies[0].key == "correct.invalid"
        assert step.session.sheet_recommendations[0].rate_kg_per_rai == Decimal("50")


# --- cancel and restart ---
def test_cancel_discards_everything_and_blocks_calculation():
    step = reduce(at_confirm().session, Button("cancel"), DATA)
    s = step.session
    assert s.state == State.CANCELLED
    assert s.values == {} and s.sheet_recommendations == [] and s.area_rai is None
    assert keys(step) == ["cancel.done"] and step.commands == []
    calc = reduce(s, Button("calculate"), DATA)
    assert keys(calc) == ["session.cancelled_start_again"] and calc.commands == []
    typed = reduce(s, Text("5"), DATA)
    assert keys(typed) == ["session.cancelled_start_again"] and typed.commands == []


@pytest.mark.parametrize("cmd", ["เริ่มใหม่", "restart", " Restart "])
def test_restart_command_is_checked_first(cmd):
    area = at_area_question().session
    assert area.pending is not None
    step = reduce(area, Text(cmd), DATA)
    assert step.session.id != area.id
    assert step.session.state == State.IMAGE_RECEIVED and step.session.source is None
    assert step.session.values == {} and step.session.area_rai is None
    assert step.session.pending is None
    assert step.replies[0].key == "start.restarted" and step.commands == []


def test_restart_in_correction_is_not_taken_as_a_value():
    base, _ = run(at_confirm().session, Button("correct"), Text("ph"))
    step = reduce(base.session, Text("restart"), DATA)
    assert step.replies[0].key == "start.restarted"


def test_restart_after_result_starts_new_session():
    result = at_result().session
    step = reduce(result, Button("restart"), DATA)
    assert step.replies[0].params["after_result"] is True
    assert step.session.id != result.id and step.session.area_rai is None


# --- area step ---
def test_confirm_asks_area_and_sets_no_area():
    step = at_area_question()
    assert keys(step) == ["area.ask"]
    assert step.session.state == State.AREA_REQUESTED
    assert step.session.area_rai is None
    assert step.commands == []


def test_area_parsed_shown_back_and_advice_built():
    step = reduce(at_area_question().session, Text("3 ไร่ 2 งาน"), DATA)
    assert step.session.state == State.AREA_SET
    assert step.session.area_rai == Decimal("3.5")
    assert step.replies[0].key == "area.accepted"
    assert step.replies[0].params == {"input": "3 ไร่ 2 งาน", "area_rai": 3.5}
    assert step.commands == [BuildAdvice()]


def test_no_result_before_area_rai():
    # BuildAdvice never comes out of any step while area_rai is None.
    steps = []
    s = Session()
    for ev in (ImageUploaded("a"), good_read(), Button("calculate"), Button("confirm"),
               Button("calculate"), Text("abc"), Text("0"), Button("calculate")):
        step = reduce(s, ev, DATA)
        s = step.session
        steps.append(step)
        if s.area_rai is None:
            assert BuildAdvice() not in step.commands
        assert s.state != State.RESULT_SENT
    # Calculate before confirm shows the confirm step, after confirm asks the size.
    assert keys(steps[2]) == ["confirm.values"]
    assert keys(steps[4]) == ["area.ask"]
    # An Explained event without an area cannot make a result.
    early = reduce(at_area_question().session, Explained(advice=None), DATA)
    assert early.session.state == State.AREA_REQUESTED


@pytest.mark.parametrize("bad", ["", "0", "-3", "abc", "5 ปอนด์"])
def test_invalid_area_keeps_asking(bad):
    step = reduce(at_area_question().session, Text(bad), DATA)
    assert step.replies[0].key == "area.invalid"
    assert step.replies[0].buttons == []
    assert step.session.state == State.AREA_REQUESTED and step.session.area_rai is None
    assert step.commands == []


def test_three_area_misses_add_restart_and_cancel():
    step, steps = run(at_area_question().session, Text("a"), Text("b"), Text("c"))
    assert steps[1].replies[0].buttons == []
    assert [b.action for b in step.replies[0].buttons] == ["restart", "cancel"]
    assert step.session.area_rai is None


def test_cancel_from_area_step():
    step = reduce(at_area_question().session, Button("cancel"), DATA)
    assert step.session.state == State.CANCELLED and step.session.area_rai is None


# --- result and changed field size ---
def test_result_sent_after_explained_only_from_area_set():
    step = at_result()
    assert step.session.state == State.RESULT_SENT
    assert step.session.area_rai == Decimal("5")
    assert [b.action for b in step.replies[0].buttons] == ["change_area", "restart"]


def test_explain_failed_moves_to_failed():
    area_set = reduce(at_area_question().session, Text("5"), DATA).session
    step = reduce(area_set, ExplainFailed("boom"), DATA)
    assert step.session.state == State.FAILED
    assert keys(step) == ["error.advice_failed"]


def test_changed_field_size_rebuilds_without_reading_again():
    result = at_result().session
    ask = reduce(result, Button("change_area"), DATA)
    assert keys(ask) == ["area.ask"] and ask.commands == []
    step = reduce(ask.session, Text("2 เฮกตาร์"), DATA)
    assert step.session.area_rai == Decimal("12.5")
    assert step.session.state == State.AREA_SET
    assert step.commands == [BuildAdvice()]
    assert not any(isinstance(c, ReadImage) for c in step.commands)
    # values from the sheet are untouched
    assert step.session.values == result.values


def test_invalid_change_keeps_old_area():
    ask = reduce(at_result().session, Button("change_area"), DATA)
    step = reduce(ask.session, Text("zero"), DATA)
    assert step.session.area_rai == Decimal("5") and step.session.state == State.RESULT_SENT
    assert step.commands == []
    dropped = reduce(step.session, Button("cancel"), DATA)
    assert dropped.session.state == State.RESULT_SENT and dropped.session.pending is None


# --- typed text without a pending step ---
@pytest.mark.parametrize("session", [Session(), at_confirm().session, at_result().session])
def test_text_without_pending_gets_choose_button_reply(session):
    step = reduce(session, Text("สวัสดี"), DATA)
    assert keys(step) == ["input.choose_button"]
    assert step.commands == []
    assert step.session.state == session.state


# --- purity ---
def test_reduce_does_not_change_the_input_session():
    s = at_confirm().session
    before = s.model_copy(deep=True)
    reduce(s, Button("correct"), DATA)
    reduce(s, Button("confirm"), DATA)
    assert s == before
