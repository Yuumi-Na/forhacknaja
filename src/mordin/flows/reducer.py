"""Pure reducer for flow A (lab sheet photo). No I/O, no farmer-facing text.

`reduce(session, event, data)` returns a new `Step`. Replies carry message keys and params only;
the text lives in explain/messages.py. The input session is never changed.

Reply keys used here:
  start.restarted, upload.received, upload.ask, upload.retrying, read.failed, read.not_dld,
  retake.message, confirm.values, correct.ask_target, correct.target_invalid, correct.ask_value,
  correct.invalid, correct.too_many, area.ask, area.accepted, area.invalid, cancel.done,
  result.next_steps, session.cancelled_start_again, error.generic, error.advice_failed,
  input.choose_button, manual.ask, manual.accepted, manual.invalid, manual.missing,
  manual.too_many, manual.nothing_yet
"""

from __future__ import annotations

import math
import re
from decimal import Decimal, InvalidOperation
from typing import Any

from mordin.data import Data, normalize_texture
from mordin.fertilizer.area import AreaError, parse_area
from mordin.fertilizer.routing import NeedMoreValues, choose_path
from mordin.flows.session import Pending, Session, SheetItem, State
from mordin.flows.types import (
    AgentFailed,
    AgentReplied,
    AskAgent,
    BuildAdvice,
    Button,
    ButtonSpec,
    Event,
    Explained,
    ExplainFailed,
    ImageUploaded,
    ReadFailed,
    ReadImage,
    ReadSucceeded,
    Reply,
    Step,
    Text,
)

# The Thai command is written as escapes so flows/ holds no Thai text.
RESTART_COMMANDS = frozenset({"\u0e40\u0e23\u0e34\u0e48\u0e21\u0e43\u0e2b\u0e21\u0e48", "restart"})
SOIL_FIELDS = ("om", "p", "k", "ca", "mg", "ph", "soil_texture")
NUMERIC_FIELDS = ("om", "p", "k", "ca", "mg", "ph")
MAX_MISSES = 3  # invalid answers in a row
MAX_READ_RETRIES = 2  # model failures that still offer a retry button
RETAKES_BEFORE_MANUAL = 2  # unreadable reads in a row before the manual entry button
_MANUAL_FIELD = re.compile(r"(?<![a-z])(om|ph|ca|mg|p|k)\s*[:=]?\s*(-?\d+(?:\.\d+)?)")
_GRADE = re.compile(r"^\d{1,2}-\d{1,2}-\d{1,2}$")
_THAI_DIGITS = str.maketrans(
    "\u0e50\u0e51\u0e52\u0e53\u0e54\u0e55\u0e56\u0e57\u0e58\u0e59", "0123456789"
)

_DEAD_STATES = (State.CANCELLED, State.FAILED)


# --- small builders -----------------------------------------------------------------
def _btn(label: str, action: str, payload: str | None = None, **params: Any) -> ButtonSpec:
    return ButtonSpec(f"button.{label}", action, payload, params)


def _restart_btn() -> ButtonSpec:
    return _btn("restart", "restart")


def _cancel_btn() -> ButtonSpec:
    return _btn("cancel", "cancel")


def _upload_btn() -> ButtonSpec:
    return _btn("upload_sheet", "upload_sheet")


def _manual_btn() -> ButtonSpec:
    return _btn("manual_entry", "manual_entry")


def _choose_button() -> Reply:
    return Reply("input.choose_button")


def _step(s: Session, *replies: Reply, commands: list | None = None) -> Step:
    return Step(session=s, replies=list(replies), commands=list(commands or []))


def _discard(s: Session) -> None:
    """Drop every value, the recommendation, the area and the image name."""
    s.values = {}
    s.value_origin = {}
    s.sheet_recommendations = []
    s.area_rai = None
    s.pending = None
    s.upload_name = None


def _build_commands(s: Session) -> list:
    """BuildAdvice only when the state is area_set and area_rai is set."""
    if s.state == State.AREA_SET and s.area_rai is not None:
        return [BuildAdvice()]
    return []


# --- value checks -------------------------------------------------------------------
def _is_number(v: Any) -> bool:
    return isinstance(v, (int, float, Decimal)) and not isinstance(v, bool) and math.isfinite(v)


def _in_range(name: str, v: Any, data: Data) -> bool:
    if not _is_number(v):
        return False
    rng = data.limits["valid_ranges"].get(name)
    return rng is None or rng["min"] <= v <= rng["max"]


def _valid_field(name: str, v: Any, data: Data) -> bool:
    if name == "soil_texture":
        return isinstance(v, str) and v in data.limits["soil_textures"]
    return _in_range(name, v, data)


def _rate_max(data: Data) -> Decimal:
    return Decimal(str(data.limits["sheet_rate_kg_per_rai"]["max"]))


def _item_ok(item: SheetItem) -> bool:
    return bool(item.fertilizer.strip()) and item.rate_kg_per_rai > 0


def _unreadable_fields(ev: ReadSucceeded, data: Data) -> dict[str, str]:
    """Fields that block the confirm step, with the reason ("" if none given)."""
    bad: dict[str, str] = {}
    for name in SOIL_FIELDS:
        if name in ev.unreadable or not _valid_field(name, ev.values.get(name), data):
            bad[name] = ev.unreadable.get(name, "")
    if not ev.sheet_recommendations or not all(_item_ok(i) for i in ev.sheet_recommendations):
        bad["sheet_recommendations"] = ev.unreadable.get("sheet_recommendations", "")
    return bad


def _parse_decimal(text: str) -> Decimal | None:
    t = text.translate(_THAI_DIGITS).strip().replace(",", "")
    try:
        d = Decimal(t)
    except InvalidOperation:
        return None
    return d if d.is_finite() else None


# --- confirm step -------------------------------------------------------------------
def _confirm_reply(s: Session, data: Data) -> Reply:
    rate_max = _rate_max(data)
    items = [
        {
            "index": i + 1,
            "fertilizer": item.fertilizer,
            "rate_kg_per_rai": float(item.rate_kg_per_rai),
            "origin": item.origin,
            # Requirement 4.3: greater than 0 and outside the plausible range.
            "rate_warning": item.rate_kg_per_rai > rate_max,
        }
        for i, item in enumerate(s.sheet_recommendations)
    ]
    return Reply(
        "confirm.values",
        {
            "values": {n: s.values.get(n) for n in SOIL_FIELDS},
            "origins": {n: s.value_origin.get(n, "read") for n in SOIL_FIELDS},
            "items": items,
            "rate_max_kg_per_rai": float(rate_max),
        },
        [_btn("confirm", "confirm"), _btn("correct", "correct"), _cancel_btn()],
    )


def _area_ask() -> Reply:
    return Reply("area.ask")


def _next_steps() -> Reply:
    return Reply("result.next_steps", buttons=[_btn("change_area", "change_area"), _restart_btn()])


def _target_buttons(s: Session) -> list[ButtonSpec]:
    buttons = [ButtonSpec(f"target.{n}", "correct_target", n) for n in SOIL_FIELDS]
    for i in range(len(s.sheet_recommendations)):
        buttons.append(ButtonSpec("target.rate", "correct_target", f"rate:{i}", {"index": i + 1}))
        buttons.append(
            ButtonSpec("target.fertilizer", "correct_target", f"fertilizer:{i}", {"index": i + 1})
        )
    buttons.append(_cancel_btn())
    return buttons


def _parse_target(text: str, s: Session) -> str | None:
    t = text.strip().lower().replace(" ", "")
    if t in SOIL_FIELDS:
        return t
    if t == "texture":
        return "soil_texture"
    m = re.fullmatch(r"(rate|fertilizer)(\d*)", t)
    if not m:
        return None
    kind, num = m.groups()
    if num:
        idx = int(num) - 1
    elif len(s.sheet_recommendations) == 1:
        idx = 0
    else:
        return None
    return f"{kind}:{idx}" if 0 <= idx < len(s.sheet_recommendations) else None


def _target_ok(target: str, s: Session) -> bool:
    if target in SOIL_FIELDS:
        return True
    m = re.fullmatch(r"(rate|fertilizer):(\d+)", target)
    return bool(m) and int(m.group(2)) < len(s.sheet_recommendations)


def _expectation(target: str, data: Data) -> dict[str, Any]:
    """What an accepted value looks like, for the 'ask again' messages."""
    if target == "soil_texture":
        return {"textures": list(data.limits["soil_textures"])}
    if target.startswith("rate:"):
        return {"min_exclusive": 0, "max": float(_rate_max(data))}
    if target.startswith("fertilizer:"):
        return {"form": "NN-NN-NN", "known": sorted(data.prices["prices_per_kg"])}
    rng = data.limits["valid_ranges"].get(target, {})
    return {"min": rng.get("min"), "max": rng.get("max")}


def _apply_correction(s: Session, target: str, text: str, data: Data) -> bool:
    """Store the typed replacement if valid. Return False and change nothing otherwise."""
    if target == "soil_texture":
        value = normalize_texture(text, data.limits["soil_textures"])
        if value is None:
            return False
        s.set_farmer_value(target, value)
        return True
    if target in NUMERIC_FIELDS:
        d = _parse_decimal(text)
        if d is None or not _in_range(target, float(d), data):
            return False
        s.set_farmer_value(target, float(d))
        return True
    kind, idx_text = target.split(":")
    item = s.sheet_recommendations[int(idx_text)]
    if kind == "rate":
        d = _parse_decimal(text)
        if d is None or not (0 < d <= _rate_max(data)):
            return False
        item.rate_kg_per_rai = d
    else:
        name = text.strip().lower()
        if not (_GRADE.match(name) or name in data.prices["prices_per_kg"]):
            return False
        item.fertilizer = name
    item.origin = "farmer"
    return True


# --- manual entry (flows B and C) --------------------------------------------------
def _range_of(name: str, data: Data) -> dict[str, Any]:
    rng = data.limits["valid_ranges"].get(name, {})
    return {"min": rng.get("min"), "max": rng.get("max")}


def _manual_ask(data: Data) -> Reply:
    fields = {n: _range_of(n, data) for n in NUMERIC_FIELDS}
    return Reply("manual.ask", {"fields": fields}, [_cancel_btn(), _restart_btn()])


def _manual_buttons(s: Session) -> list[ButtonSpec]:
    buttons = [_btn("done", "manual_done")] if s.values else []
    return [*buttons, _cancel_btn()]


def _manual_echo(s: Session) -> Reply:
    shown = {n: s.values[n] for n in NUMERIC_FIELDS if n in s.values}
    return Reply("manual.accepted", {"values": shown}, _manual_buttons(s))


def _start_manual(s: Session, data: Data) -> Step:
    if s.state in (*_DEAD_STATES, State.RESULT_SENT):
        s = Session()
    _discard(s)
    s.state = State.VALUES_READ  # collecting typed values; source tells it apart from a sheet
    s.source = "manual"
    s.reads_failed_in_a_row = 0
    s.vision_retries = 0
    s.pending = Pending(kind="manual_values")
    return _step(s, _manual_ask(data))


def _in_manual(s: Session) -> bool:
    return s.state == State.VALUES_READ and s.source == "manual"


def _on_manual_text(s: Session, text: str, data: Data) -> Step:
    assert s.pending is not None
    if not _in_manual(s):
        return _step(s, _choose_button())
    found = _MANUAL_FIELD.findall(text.translate(_THAI_DIGITS).lower())
    rejected: dict[str, dict[str, Any]] = {}
    accepted = 0
    for name, num in found:
        if _in_range(name, float(num), data):
            s.set_farmer_value(name, float(num))
            accepted += 1
        else:
            rejected[name] = _range_of(name, data)
    replies: list[Reply] = []
    if not found:
        rejected = {n: _range_of(n, data) for n in NUMERIC_FIELDS}
    if rejected:
        replies.append(Reply("manual.invalid", {"fields": rejected, "unrecognized": not found}))
    if accepted:
        s.pending = s.pending.model_copy(update={"misses": 0})
        replies.append(_manual_echo(s))
        return _step(s, *replies)
    misses = s.pending.misses + 1
    if misses >= MAX_MISSES:
        s.pending = None  # back to the buttons; accepted values stay
        replies.append(Reply("manual.too_many", buttons=_manual_buttons(s) + [_restart_btn()]))
        return _step(s, *replies)
    s.pending = s.pending.model_copy(update={"misses": misses})
    return _step(s, *replies)


def _go_to_area(s: Session) -> Step:
    s.state = State.CONFIRMED  # typed values need no separate confirm step
    s.state = State.AREA_REQUESTED
    s.pending = Pending(kind="area_answer")
    return _step(s, _area_ask())


def _manual_done(s: Session, data: Data) -> Step:
    if not _in_manual(s):
        return _stale(s)
    if not s.values:
        s.pending = Pending(kind="manual_values")
        return _step(s, Reply("manual.nothing_yet", buttons=[_cancel_btn()]))
    path = choose_path("manual", s.values, [], data.basic_formula["required_fields"])
    if isinstance(path, NeedMoreValues):
        s.pending = Pending(kind="manual_values")
        buttons = [_cancel_btn()]
        if s.values.get("ph") is not None:
            buttons.insert(0, _btn("ph_only", "manual_ph_only"))
        return _step(s, Reply("manual.missing", {"missing": list(path.missing),
                                                 "ph_present": s.values.get("ph") is not None},
                              buttons))
    return _go_to_area(s)


def _manual_ph_only(s: Session) -> Step:
    """Farmer chose pH-only advice. Other typed values are dropped, only pH is kept."""
    if not _in_manual(s) or s.values.get("ph") is None:
        return _stale(s)
    ph = s.values["ph"]
    s.values = {}
    s.value_origin = {}
    s.set_farmer_value("ph", ph)
    return _go_to_area(s)


# --- handlers -----------------------------------------------------------------------
def _restart(s: Session) -> Step:
    """New session with nothing from the old one. The page keeps old messages."""
    return _step(Session(), Reply("start.restarted", {"after_result": s.state == State.RESULT_SENT},
                                  [_upload_btn()]))


def _begin_read(s: Session, filename: str) -> Step:
    _discard(s)
    s.state = State.IMAGE_RECEIVED
    s.source = "lab_sheet"
    s.upload_name = filename
    s.vision_retries = 0
    return _step(s, Reply("upload.received"), commands=[ReadImage(filename)])


def _on_upload(s: Session, ev: ImageUploaded) -> Step:
    if s.state in (State.IMAGE_RECEIVED, State.RETAKE_NEEDED, State.VALUES_READ):
        # A new photo replaces everything read from the earlier one (3.4).
        return _begin_read(s, ev.filename)
    if s.state in (*_DEAD_STATES, State.RESULT_SENT):
        return _begin_read(Session(), ev.filename)
    return _step(s, _choose_button())


def _on_read_succeeded(s: Session, ev: ReadSucceeded, data: Data) -> Step:
    if s.state != State.IMAGE_RECEIVED or s.source != "lab_sheet":
        return _step(s)  # late result for a session that moved on
    if not ev.is_dld_sheet:
        _discard(s)
        s.source = None
        s.reads_failed_in_a_row = 0
        return _step(s, Reply("read.not_dld", buttons=[_upload_btn(), _manual_btn()]))

    bad = _unreadable_fields(ev, data)
    if bad:
        _discard(s)
        s.state = State.RETAKE_NEEDED
        s.reads_failed_in_a_row += 1
        buttons = [_upload_btn()]
        if s.reads_failed_in_a_row >= RETAKES_BEFORE_MANUAL:
            buttons.append(_manual_btn())
        return _step(s, Reply("retake.message", {"unreadable": list(bad), "reasons": bad}, buttons))

    for name in SOIL_FIELDS:
        s.set_read_value(name, ev.values[name])
    s.sheet_recommendations = [
        SheetItem(fertilizer=i.fertilizer.strip(), rate_kg_per_rai=i.rate_kg_per_rai, origin="read")
        for i in ev.sheet_recommendations
    ]
    s.state = State.VALUES_READ
    s.reads_failed_in_a_row = 0
    s.vision_retries = 0
    s.pending = None
    return _step(s, _confirm_reply(s, data))


def _on_read_failed(s: Session) -> Step:
    if s.state != State.IMAGE_RECEIVED:
        return _step(s)
    s.vision_retries += 1
    buttons = []
    if s.vision_retries <= MAX_READ_RETRIES:
        buttons.append(_btn("retry", "retry_read"))
    buttons.append(_manual_btn())
    return _step(s, Reply("read.failed", {"attempt": s.vision_retries}, buttons))


def _cancel(s: Session) -> Step:
    if s.state == State.RESULT_SENT:
        # Only drops a pending field size change. The result stays as it was.
        s.pending = None
        return _step(s, _next_steps())
    _discard(s)
    s.state = State.CANCELLED
    return _step(s, Reply("cancel.done", buttons=[_restart_btn()]))


def _confirm(s: Session, data: Data) -> Step:
    if s.state == State.VALUES_READ and s.source == "lab_sheet":
        s.state = State.CONFIRMED  # confirmed, then the field size is asked at once
        s.state = State.AREA_REQUESTED
        s.pending = Pending(kind="area_answer")
        return _step(s, _area_ask())
    return _stale(s)


def _stale(s: Session) -> Step:
    """A button or text that does not fit the current step."""
    if s.pending is not None and s.pending.kind == "area_answer":
        return _step(s, _area_ask())
    return _step(s, _choose_button())


def _calculate(s: Session, data: Data) -> Step:
    """A request for totals. Refused unless the state is area_set with an area."""
    if s.state == State.AREA_SET and s.area_rai is not None:
        return _step(s, commands=_build_commands(s))
    if s.area_rai is None and s.state == State.AREA_REQUESTED:
        return _step(s, _area_ask())
    if s.state == State.VALUES_READ and s.source == "lab_sheet":
        return _step(s, _confirm_reply(s, data))
    return _stale(s)


def _on_button(s: Session, ev: Button, data: Data) -> Step:
    a = ev.action
    if a == "cancel":
        return _cancel(s)
    if a == "upload_sheet":
        return _step(s, Reply("upload.ask"))
    if a == "retry_read":
        if s.state == State.IMAGE_RECEIVED and s.upload_name and s.vision_retries <= MAX_READ_RETRIES:
            return _step(s, Reply("upload.retrying"), commands=[ReadImage(s.upload_name)])
        return _step(s, _choose_button())
    if a == "confirm":
        return _confirm(s, data)
    if a == "calculate":
        return _calculate(s, data)
    if a == "correct":
        if s.state != State.VALUES_READ or s.source != "lab_sheet":
            return _stale(s)
        s.pending = Pending(kind="correction_target")
        return _step(s, Reply("correct.ask_target", buttons=_target_buttons(s)))
    if a == "correct_target":
        if s.state != State.VALUES_READ or s.source != "lab_sheet" or not ev.payload or not _target_ok(ev.payload, s):
            return _stale(s)
        s.pending = Pending(kind="correction_value", field=ev.payload)
        return _step(s, Reply("correct.ask_value", {"target": ev.payload,
                                                    **_expectation(ev.payload, data)}))
    if a == "manual_entry":
        return _start_manual(s, data)
    if a == "manual_done":
        return _manual_done(s, data)
    if a == "manual_ph_only":
        return _manual_ph_only(s)
    if a == "change_area":
        if s.state != State.RESULT_SENT:
            return _stale(s)
        s.pending = Pending(kind="area_answer")
        return _step(s, _area_ask())
    return _step(s, _choose_button())


def _on_area_text(s: Session, text: str) -> Step:
    assert s.pending is not None
    if s.state not in (State.AREA_REQUESTED, State.RESULT_SENT):
        return _step(s, _choose_button())
    try:
        value = parse_area(text)
    except AreaError:
        s.pending = s.pending.model_copy(update={"misses": s.pending.misses + 1})
        buttons = [_restart_btn(), _cancel_btn()] if s.pending.misses >= MAX_MISSES else []
        return _step(s, Reply("area.invalid", {"misses": s.pending.misses}, buttons))
    s.area_rai = Decimal(str(value))
    s.state = State.AREA_SET
    s.pending = None
    reply = Reply("area.accepted", {"input": text.strip(), "area_rai": value})
    return _step(s, reply, commands=_build_commands(s))


def _on_correction_text(s: Session, text: str, data: Data) -> Step:
    assert s.pending is not None
    if s.state != State.VALUES_READ:
        return _step(s, _choose_button())
    pending = s.pending

    if pending.kind == "correction_target":
        target = _parse_target(text, s)
        if target is None:
            misses = pending.misses + 1
            if misses >= MAX_MISSES:
                s.pending = None
                return _step(s, Reply("correct.too_many", {"target": None}), _confirm_reply(s, data))
            s.pending = pending.model_copy(update={"misses": misses})
            return _step(s, Reply("correct.target_invalid", buttons=_target_buttons(s)))
        s.pending = Pending(kind="correction_value", field=target)
        return _step(s, Reply("correct.ask_value", {"target": target, **_expectation(target, data)}))

    target = pending.field or ""
    if _target_ok(target, s) and _apply_correction(s, target, text, data):
        s.pending = None
        return _step(s, _confirm_reply(s, data))
    misses = pending.misses + 1
    if misses >= MAX_MISSES:
        s.pending = None  # stored value stays as it was
        return _step(s, Reply("correct.too_many", {"target": target}), _confirm_reply(s, data))
    s.pending = pending.model_copy(update={"misses": misses})
    return _step(s, Reply("correct.invalid", {"target": target, **_expectation(target, data)}))


def _on_text(s: Session, ev: Text, data: Data) -> Step:
    if s.pending is None:
        # Text that answers no pending step is chat. Every figure in the flow still comes from code.
        if not ev.text.strip():
            return _step(s, _choose_button())
        return _step(s, commands=[AskAgent(ev.text)])
    if s.pending.kind == "area_answer":
        return _on_area_text(s, ev.text)
    if s.pending.kind == "manual_values":
        return _on_manual_text(s, ev.text, data)
    if s.pending.kind in ("correction_target", "correction_value"):
        return _on_correction_text(s, ev.text, data)
    return _step(s, _choose_button())


def _on_explained(s: Session, ev: Explained) -> Step:
    if s.state != State.AREA_SET or s.area_rai is None:
        return _step(s)  # late or out-of-order: no result without area_rai
    s.state = State.RESULT_SENT
    s.pending = None
    return _step(s, _next_steps())


def _on_explain_failed(s: Session) -> Step:
    if s.state != State.AREA_SET:
        return _step(s)
    s.state = State.FAILED
    s.pending = None
    return _step(s, Reply("error.advice_failed", buttons=[_restart_btn()]))


def _on_agent_failed(s: Session) -> Step:
    return _step(s, _choose_button())  # the same fixed reply as when no agent is set up


def _dead(s: Session) -> Step:
    """Cancelled or failed session: reject everything except restart and a new upload."""
    key = "session.cancelled_start_again" if s.state == State.CANCELLED else "error.generic"
    return _step(s, Reply(key, buttons=[_restart_btn()]))


# --- entry point --------------------------------------------------------------------
def reduce(session: Session, event: Event, data: Data) -> Step:
    s = session.model_copy(deep=True)

    # The restart command comes before anything else.
    if isinstance(event, Text) and event.text.strip().casefold() in RESTART_COMMANDS:
        return _restart(s)
    if isinstance(event, Button) and event.action == "restart":
        return _restart(s)

    if isinstance(event, ImageUploaded):
        return _on_upload(s, event)
    if isinstance(event, ReadSucceeded):
        return _on_read_succeeded(s, event, data)
    if isinstance(event, ReadFailed):
        return _on_read_failed(s)
    if isinstance(event, Explained):
        return _on_explained(s, event)
    if isinstance(event, ExplainFailed):
        return _on_explain_failed(s)
    if isinstance(event, AgentReplied):
        return _step(s)  # the service shows the text; the session does not change
    if isinstance(event, AgentFailed):
        return _on_agent_failed(s)

    if isinstance(event, Button) and event.action == "manual_entry":
        return _start_manual(s, data)
    if s.state in _DEAD_STATES:
        return _dead(s)
    if isinstance(event, Button):
        return _on_button(s, event, data)
    if isinstance(event, Text):
        return _on_text(s, event, data)
    return _step(s)
