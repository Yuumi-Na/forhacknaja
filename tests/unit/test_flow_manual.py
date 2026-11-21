from decimal import Decimal

from mordin.data import load_data
from mordin.flows import (
    BuildAdvice,
    Button,
    ImageUploaded,
    ReadFailed,
    ReadImage,
    Session,
    State,
    Text,
    reduce,
)

DATA = load_data()


def run(session, *events):
    step = None
    for ev in events:
        step = reduce(session, ev, DATA)
        session = step.session
    return step


def keys(step):
    return [r.key for r in step.replies]


def actions(step):
    return [b.action for r in step.replies for b in r.buttons]


def start():
    return run(Session(), Button("manual_entry"))


def test_manual_entry_lists_all_six_fields():
    step = start()
    assert keys(step) == ["manual.ask"]
    assert set(step.replies[0].params["fields"]) == {"om", "p", "k", "ca", "mg", "ph"}
    assert step.session.source == "manual"
    assert step.session.pending.kind == "manual_values"
    assert step.commands == []


def test_accepted_values_are_echoed_and_done_offered():
    step = run(start().session, Text("om 1.2 p 8"))
    assert keys(step) == ["manual.accepted"]
    assert step.replies[0].params["values"] == {"om": 1.2, "p": 8.0}
    assert "manual_done" in actions(step)
    assert step.session.value_origin["om"] == "farmer"


def test_no_done_button_before_any_value():
    step = run(start().session, Text("hello"))
    assert keys(step) == ["manual.invalid"]
    assert "manual_done" not in actions(step)


def test_out_of_range_rejected_and_earlier_values_kept():
    s = run(start().session, Text("om 1.2")).session
    step = run(s, Text("ph 99, k 60"))
    assert keys(step) == ["manual.invalid", "manual.accepted"]
    assert "ph" in step.replies[0].params["fields"]
    assert step.session.values == {"om": 1.2, "k": 60.0}
    step = run(step.session, Text("om 500"))
    assert step.session.values["om"] == 1.2


def test_ph_not_confused_with_p():
    step = run(start().session, Text("pH 5.4"))
    assert step.session.values == {"ph": 5.4}


def test_three_misses_return_to_buttons():
    s = start().session
    for _ in range(2):
        s = run(s, Text("abc")).session
        assert s.pending is not None
    step = run(s, Text("abc"))
    assert step.session.pending is None
    assert keys(step)[-1] == "manual.too_many"
    assert run(step.session, Text("om 1")).replies[0].key == "input.choose_button"


def test_done_with_full_values_goes_to_area_without_totals():
    s = run(start().session, Text("om 1.2 p 8 k 60 ca 400 mg 70")).session
    step = run(s, Button("manual_done"))
    assert step.session.state == State.AREA_REQUESTED
    assert keys(step) == ["area.ask"]
    assert step.commands == []
    assert step.session.area_rai is None


def test_manual_then_area_builds_advice():
    s = run(start().session, Text("om 1.2 p 8 k 60 ca 400 mg 70"), Button("manual_done")).session
    step = run(s, Text("5"))
    assert step.session.state == State.AREA_SET
    assert step.session.area_rai == Decimal("5")
    assert step.commands == [BuildAdvice()]


def test_done_with_only_ph_routes_to_ph_only():
    s = run(start().session, Text("ph 5.2")).session
    step = run(s, Button("manual_done"))
    assert step.session.state == State.AREA_REQUESTED


def test_missing_fields_named_and_calculation_blocked():
    s = run(start().session, Text("om 1.2 ph 5.2")).session
    step = run(s, Button("manual_done"))
    assert keys(step) == ["manual.missing"]
    assert step.replies[0].params["missing"] == ["p", "k", "ca", "mg"]
    assert "manual_ph_only" in actions(step)
    assert step.session.state == State.VALUES_READ
    assert step.commands == []
    assert step.session.pending.kind == "manual_values"


def test_missing_fields_without_ph_has_no_ph_only_button():
    s = run(start().session, Text("om 1.2")).session
    step = run(s, Button("manual_done"))
    assert "manual_ph_only" not in actions(step)


def test_ph_only_button_keeps_only_ph():
    s = run(start().session, Text("om 1.2 ph 5.2"), Button("manual_done")).session
    step = run(s, Button("manual_ph_only"))
    assert step.session.values == {"ph": 5.2}
    assert step.session.state == State.AREA_REQUESTED
    assert keys(step) == ["area.ask"]


def test_confirm_and_correct_ignored_for_manual():
    s = run(start().session, Text("om 1")).session
    assert run(s, Button("confirm")).session.state == State.VALUES_READ
    assert keys(run(s, Button("calculate"))) == ["input.choose_button"]


def test_restart_checked_first_while_collecting():
    step = run(start().session, Text("restart"))
    assert keys(step) == ["start.restarted"]
    assert step.session.values == {}


def test_cancel_discards_manual_values():
    s = run(start().session, Text("om 1")).session
    step = run(s, Button("cancel"))
    assert step.session.state == State.CANCELLED
    assert step.session.values == {}


def test_read_failure_retries_then_manual_only():
    s = run(Session(), ImageUploaded("a.jpg")).session
    step = run(s, ReadFailed())
    assert actions(step) == ["retry_read", "manual_entry"]
    step = run(step.session, Button("retry_read"))
    assert step.commands == [ReadImage("a.jpg")]
    step = run(step.session, ReadFailed())
    assert actions(step) == ["retry_read", "manual_entry"]
    step = run(step.session, Button("retry_read"), ReadFailed())
    assert actions(step) == ["manual_entry"]
    assert run(step.session, Button("retry_read")).commands == []


def test_manual_entry_available_from_failed_read_and_cancelled():
    s = run(Session(), ImageUploaded("a.jpg"), ReadFailed()).session
    assert run(s, Button("manual_entry")).session.source == "manual"
    s = run(start().session, Button("cancel")).session
    assert run(s, Button("manual_entry")).session.state == State.VALUES_READ
