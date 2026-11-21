"""Event loop: runs the commands the reducer returns and feeds the results back.

`Service.handle` reduces one event, runs any `ReadImage` or `BuildAdvice` command, reduces the
result event, and repeats until no command is left. Image bytes live only in `ImageHolder`,
never in the session or the store. Error logs hold the failure type, session id and step name,
never a soil value or image data.
"""

from __future__ import annotations

import logging
import time
from decimal import Decimal
from typing import Any, Callable

from mordin import config
from mordin.data import Data, load_data
from mordin.explain import messages
from mordin.explain.advice import ModelCaller, build_advice, default_model_caller
from mordin.fertilizer.amendments import build_ph_plan
from mordin.fertilizer.formula import calculate_basic, soil_status
from mordin.fertilizer.plan import Plan
from mordin.fertilizer.routing import NeedMoreValues, choose_path
from mordin.fertilizer.sheet_plan import build_sheet_plan
from mordin.fertilizer.totals import compute_item
from mordin.flows import (
    BuildAdvice,
    Command,
    Event,
    Explained,
    ExplainFailed,
    ImageUploaded,
    ReadFailed,
    ReadImage,
    ReadSucceeded,
    Reply,
    Session,
    SheetItem,
    State,
    reduce,
)
from mordin.flows.reducer import MAX_READ_RETRIES
from mordin.flows.types import ButtonSpec, Step
from mordin.storage.store import InMemoryStore, SessionStore
from mordin.vision import reader as vision_reader
from mordin.vision import stub as vision_stub
from mordin.vision.image import ImageError, PreparedImage, prepare_image
from mordin.vision.schemas import UNREADABLE, SheetReading

log = logging.getLogger("mordin.service")

WARN_AFTER_SECONDS = 30.0
MAX_COMMAND_ROUNDS = 10  # guard against a loop between reducer and commands

Bubble = dict[str, Any]


class PlanError(Exception):
    """No plan can be built from the session."""


class ImageHolder:
    """Prepared images in memory, by session id. Never stored with the session."""

    def __init__(self) -> None:
        self._images: dict[str, PreparedImage] = {}

    def put(self, session_id: str, image: PreparedImage) -> None:
        self._images[session_id] = image

    def get(self, session_id: str) -> PreparedImage | None:
        return self._images.get(session_id)

    def delete(self, session_id: str) -> None:
        self._images.pop(session_id, None)

    def move(self, old_id: str, new_id: str) -> None:
        image = self._images.pop(old_id, None)
        if image is not None:
            self._images[new_id] = image

    def __contains__(self, session_id: str) -> bool:
        return session_id in self._images


# --- pure helpers -------------------------------------------------------------------
def reading_to_event(reading: SheetReading) -> ReadSucceeded:
    """Turn a vision reading into the reducer event. "unreadable" becomes None."""
    reason = reading.reason_code or ""
    values: dict[str, Any] = {}
    unreadable: dict[str, str] = {}
    for name in ("om", "p", "k", "ca", "mg", "ph", "soil_texture"):
        v = getattr(reading, name)
        if v == UNREADABLE:
            values[name] = None
            unreadable[name] = reason
        else:
            values[name] = v

    recs: list[SheetItem] = []
    raw = reading.sheet_recommendations
    if raw == UNREADABLE or not raw:
        unreadable["sheet_recommendations"] = reason
    elif any(i.rate_kg_per_rai == UNREADABLE for i in raw):
        unreadable["sheet_recommendations"] = reason
    else:
        recs = [
            SheetItem(fertilizer=i.fertilizer, rate_kg_per_rai=Decimal(str(i.rate_kg_per_rai)))
            for i in raw
        ]
    return ReadSucceeded(
        values=values,
        sheet_recommendations=recs,
        is_dld_sheet=reading.reason_code != "not_dld_sheet",
        unreadable=unreadable,
    )


def plan_for(session: Session, data: Data) -> Plan:
    """Build the Plan for a session that has `area_rai`. Raises PlanError if it cannot."""
    area = session.area_rai
    if area is None:
        raise PlanError("area_rai missing")
    path = choose_path(
        session.source,
        session.values,
        session.sheet_recommendations,
        data.basic_formula["required_fields"],
    )
    if isinstance(path, NeedMoreValues):
        raise PlanError("not enough values")
    per_kg = data.prices.get("prices_per_kg", {})
    if path == "sheet":
        return build_sheet_plan(session.sheet_recommendations, area, data.prices, data.limits)
    if path == "ph_only":
        return build_ph_plan(session.values["ph"], area, data.amendments, data.prices, data.limits)
    result = calculate_basic(session.values, data.basic_formula, data.limits)
    items = tuple(
        compute_item(kg, area, per_kg.get(key), data.limits, key=key)
        for key, kg in result.amounts_kg_per_rai.items()
        if kg > 0
    )
    return Plan(
        source="basic_formula",
        area_rai=area,
        items=items,
        price_date=str(data.prices.get("date", "")),
        uses_demo_rules=True,
        soil_status=soil_status(session.values, data.basic_formula),
    )


def _error_bubble() -> Bubble:
    spec = Reply("error.generic", buttons=[ButtonSpec("button.restart", "restart")])
    return messages.render(spec)


# --- service ------------------------------------------------------------------------
class Service:
    def __init__(
        self,
        store: SessionStore | None = None,
        data: Data | None = None,
        *,
        stub: bool | None = None,
        model_caller: ModelCaller | None = None,
        holder: ImageHolder | None = None,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.store: SessionStore = store if store is not None else InMemoryStore()
        self.data = data if data is not None else load_data()
        self.stub = config.vision_stub_enabled() if stub is None else stub
        # The stub run uses template text, so it needs no Bedrock call.
        self.model_caller = (
            model_caller if model_caller is not None or self.stub else default_model_caller
        )
        self.holder = holder if holder is not None else ImageHolder()
        self._clock = clock

    # -- public --------------------------------------------------------------------
    def start(self) -> dict[str, Any]:
        """Create a session and return the startup bubbles."""
        session = Session()
        try:
            self.store.create(session)
        except Exception as exc:
            self._log_failure("store", "-", exc)
            return {"session_id": None, "state": State.FAILED.value, "bubbles": [_error_bubble()]}
        menu = Reply(
            "start.menu",
            buttons=[
                ButtonSpec("button.upload_sheet", "upload_sheet"),
                ButtonSpec("button.manual_entry", "manual_entry"),
            ],
        )
        bubbles = [messages.render(Reply("start.notice")), messages.render(menu)]
        return {"session_id": session.id, "state": session.state.value, "bubbles": bubbles}

    def handle(
        self, session_id: str, event: Event, image: bytes | None = None
    ) -> dict[str, Any]:
        """Run one turn. Returns {session_id, state, bubbles}."""
        started = self._clock()
        timings: dict[str, float] = {}
        try:
            session = self.store.get(session_id)
        except Exception as exc:
            self._log_failure("store", session_id, exc)
            self.holder.delete(session_id)
            return {"session_id": session_id, "state": State.FAILED.value,
                    "bubbles": [_error_bubble()]}

        if isinstance(event, ImageUploaded):
            self._hold_image(session_id, image)

        bubbles: list[Bubble] = []
        try:
            final = self._drive(session, event, bubbles, timings)
        except Exception as exc:  # a bug must not leave bytes behind or show a stack trace
            self._log_failure("turn", session_id, exc)
            self.holder.delete(session_id)
            return {"session_id": session_id, "state": State.FAILED.value,
                    "bubbles": [_error_bubble()]}

        try:
            if final.id != session_id:
                self.store.create(final)
                self.store.delete(session_id)
            else:
                self.store.save(final)
        except Exception as exc:
            self._log_failure("store", final.id, exc)
            self.holder.delete(session_id)
            self.holder.delete(final.id)
            return {"session_id": final.id, "state": State.FAILED.value,
                    "bubbles": [_error_bubble()]}

        self._log_timing(final.id, self._clock() - started, timings)
        return {"session_id": final.id, "state": final.state.value, "bubbles": bubbles}

    # -- loop ----------------------------------------------------------------------
    def _drive(
        self, session: Session, event: Event, bubbles: list[Bubble], timings: dict[str, float]
    ) -> Session:
        old_id = session.id
        t0 = self._clock()
        step = reduce(session, event, self.data)
        if session.state == State.AREA_REQUESTED:
            timings["area"] = self._clock() - t0
        rounds = 0
        while True:
            self._after_reduce(old_id, step.session)
            old_id = step.session.id
            self._add_replies(bubbles, step)
            if not step.commands or rounds >= MAX_COMMAND_ROUNDS:
                return step.session
            rounds += 1
            session = step.session
            commands: list[Command] = list(step.commands)
            result_step: Step | None = None
            for cmd in commands:
                ev, name, elapsed = self._run(cmd, session)
                timings[name] = timings.get(name, 0.0) + elapsed
                result_step = reduce(session, ev, self.data)
                if isinstance(ev, Explained) and result_step.session.state == State.RESULT_SENT:
                    bubbles.extend(messages.render_advice(ev.advice))
                session = result_step.session
                self._after_reduce(old_id, session)
                self._add_replies(bubbles, result_step)
            assert result_step is not None
            step = Step(session=session, replies=[], commands=result_step.commands)

    @staticmethod
    def _add_replies(bubbles: list[Bubble], step: Step) -> None:
        # The loop adds replies of command result steps itself; this adds the first step's.
        if step.replies:
            bubbles.extend(messages.render(r) for r in step.replies)

    def _after_reduce(self, old_id: str, session: Session) -> None:
        """Keep the image only while a read retry is still possible."""
        if session.id != old_id:
            self.holder.delete(old_id)
        keep = session.state == State.IMAGE_RECEIVED and session.vision_retries <= MAX_READ_RETRIES
        if not keep:
            self.holder.delete(session.id)

    # -- commands ------------------------------------------------------------------
    def _run(self, cmd: Command, session: Session) -> tuple[Event, str, float]:
        t0 = self._clock()
        if isinstance(cmd, ReadImage):
            ev: Event = self._read(cmd, session)
            name = "read"
        elif isinstance(cmd, BuildAdvice):
            ev = self._explain(session)
            name = "explain"
        else:  # pragma: no cover - the Command union has two members
            raise TypeError(type(cmd).__name__)
        return ev, name, self._clock() - t0

    def _read(self, cmd: ReadImage, session: Session) -> Event:
        try:
            if self.stub:
                reading = vision_stub.read_lab_sheet_stub(cmd.filename)
            else:
                image = self.holder.get(session.id)
                if image is None:
                    raise LookupError("no image held")
                reading = vision_reader.read_lab_sheet(image, self.data)
            return reading_to_event(reading)
        except Exception as exc:
            self._log_failure("read", session.id, exc)
            return ReadFailed(reason=type(exc).__name__)

    def _explain(self, session: Session) -> Event:
        try:
            plan = plan_for(session, self.data)
            advice = build_advice(
                plan, session, self.data, stub=self.stub, model_caller=self.model_caller
            )
            return Explained(advice=advice)
        except Exception as exc:
            self._log_failure("explain", session.id, exc)
            return ExplainFailed(reason=type(exc).__name__)

    # -- images --------------------------------------------------------------------
    def _hold_image(self, session_id: str, image: bytes | None) -> None:
        self.holder.delete(session_id)
        if self.stub or not image:
            return
        try:
            self.holder.put(session_id, prepare_image(image))
        except ImageError as exc:
            self._log_failure("prepare_image", session_id, exc)

    # -- logs ----------------------------------------------------------------------
    @staticmethod
    def _log_failure(step: str, session_id: str, exc: BaseException) -> None:
        # Failure type, session id and step name only. No message text, no values.
        log.error("failure step=%s session=%s type=%s", step, session_id, type(exc).__name__)

    @staticmethod
    def _log_timing(session_id: str, total: float, timings: dict[str, float]) -> None:
        parts = " ".join(f"{k}={v:.2f}s" for k, v in sorted(timings.items()))
        log.info("turn session=%s total=%.2fs %s", session_id, total, parts)
        if total > WARN_AFTER_SECONDS:
            log.warning("turn over %.0f s session=%s total=%.2fs", WARN_AFTER_SECONDS, session_id, total)
