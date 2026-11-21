"""Advice message. Every figure comes from the Plan; nothing is calculated here.

By default the soil summary, expected effect and shop script come from templates. When a
`model_caller` is given, one structured model call phrases them (Req 12.3, 13.7, 13.8, 18.4).
Each block is checked on its own and falls back to its template if it fails a check.
"""

from __future__ import annotations

import logging
import time
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeout
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping

from pydantic import BaseModel, ValidationError

from mordin.data import Data
from mordin.explain import figures, messages, templates
from mordin.explain.script import ScriptDraft, check_script, template_script
from mordin.explain.table import SummaryTable, build_table
from mordin.fertilizer.formula import soil_status
from mordin.fertilizer.plan import Plan
from mordin.fertilizer.rounding import to_decimal
from mordin.flows.session import Session


log = logging.getLogger("mordin.explain")

PROMPT_FILE = Path(__file__).resolve().parents[3] / "prompts" / "explain_v1.md"
DEADLINE_SECONDS = 10.0


class AdviceText(BaseModel):
    """Structured output of the one explain call."""

    soil_summary: str
    expected_effect: str
    shop_script: list[str]


# Takes the full user message, returns the structured text. Injected in tests.
ModelCaller = Callable[[str], AdviceText]


def load_prompt() -> str:
    return PROMPT_FILE.read_text(encoding="utf-8")


def default_model_caller(user_text: str) -> AdviceText:
    """One Bedrock call through Strands. Model ID and Region come from config only."""
    from strands import Agent

    from mordin.config import EXPLAINER_MAX_TOKENS, make_bedrock_model

    agent = Agent(
        model=make_bedrock_model(EXPLAINER_MAX_TOKENS),
        system_prompt=load_prompt(),
        callback_handler=None,
        tools=[],
    )
    result = agent(user_text, structured_output_model=AdviceText)
    out = getattr(result, "structured_output", None)
    if not isinstance(out, AdviceText):
        raise ValueError("model returned no structured output")
    return out


def _model_input(plan: Plan, statuses: Mapping[str, str]) -> str:
    """Soil statuses and the allowed figures. Figures are copied from the Plan, not computed."""
    lines = [f"source: {plan.source}", f"area_rai: {templates.fmt_decimal(plan.area_rai)}"]
    if plan.ph_class:
        lines.append(f"ph_class: {plan.ph_class}")
    for name in templates.SOIL_ORDER:
        status = statuses.get(name)
        if status in templates.STATUS_WORDS:
            lines.append(f"soil {templates.SOIL_NAMES[name]}: {templates.STATUS_WORDS[status]}")
    if plan.items:
        for item in plan.items:
            lines.append(f"item: {messages.item_name(item.key)}, script_kg: {item.script_kg}")
    else:
        lines.append("items: none")
    return "\n".join(lines)


def _text_ok(text: str) -> bool:
    return bool(text.strip()) and not figures.check_figures(text) and not figures.check_wording(text)


def _script_problems(sentences: list[str], plan: Plan) -> list[str]:
    try:
        draft = ScriptDraft(sentences=sentences)
    except ValidationError:
        return ["sentence_count"]
    return check_script(draft, plan)


def _model_blocks(
    plan: Plan, statuses: Mapping[str, str], caller: ModelCaller, deadline: float
) -> tuple[str | None, str | None, list[str] | None]:
    """Run the call (and one retry for a bad script) inside one deadline.

    Returns (soil_summary, expected_effect, shop_script), with None for a block that failed its
    check. On timeout or model error all three are None and one log entry is written.
    """
    start = time.monotonic()
    message = _model_input(plan, statuses)
    executor = ThreadPoolExecutor(max_workers=2)

    def call(text: str, timeout: float) -> AdviceText:
        return executor.submit(caller, text).result(timeout=timeout)

    try:
        try:
            first = call(message, deadline)
        except FutureTimeout:
            log.warning("explain step failed: timeout")
            return None, None, None
        except Exception as exc:  # model, network or config failure
            log.warning("explain step failed: %s", type(exc).__name__)
            return None, None, None

        summary = first.soil_summary if _text_ok(first.soil_summary) else None
        effect = first.expected_effect if _text_ok(first.expected_effect) else None
        problems = _script_problems(first.shop_script, plan)
        script: list[str] | None = first.shop_script if not problems else None

        remaining = deadline - (time.monotonic() - start)
        if problems and remaining > 0:
            retry_text = message + "\nThe previous shop_script was rejected: " + ", ".join(problems)
            try:
                second = call(retry_text, remaining)
                if not _script_problems(second.shop_script, plan):
                    script = second.shop_script
            except FutureTimeout:
                log.warning("explain retry failed: timeout")
            except Exception as exc:
                log.warning("explain retry failed: %s", type(exc).__name__)
        return summary, effect, script
    finally:
        executor.shutdown(wait=False, cancel_futures=True)


@dataclass(frozen=True)
class AdviceMessage:
    demo_label: str | None
    table: SummaryTable
    shop_script: tuple[str, ...]  # 1 to 3 sentences
    per_rai_guide: tuple[str, ...]
    soil_summary: str
    expected_effect: str
    notices: tuple[str, ...]
    ph_summary: dict[str, str] | None = None  # pH-only path: data for the pH card


def _fmt(v: Any) -> str:
    """Show a number as printed, without a trailing .0 (display only)."""
    d = to_decimal(v).normalize()
    return f"{d:f}" if d != d.to_integral() else f"{d.to_integral():f}"


def _ph_summary(plan: Plan, session: Session, data: Data, soil_summary: str) -> dict[str, str] | None:
    """pH card content for the pH-only path. Values are copied, never recalculated."""
    if plan.source != "ph_only" or plan.ph_class is None:
        return None
    ph = session.values.get("ph")
    if ph is None:
        return None
    limits = data.amendments["ph_limits"]
    def ph_text(v: Any) -> str:  # pH limits read as "6.0", not "6"
        s = _fmt(v)
        return s if "." in s else s + ".0"

    lower_text = ph_text(limits["acidic_below"])
    upper_text = ph_text(limits["alkaline_above"])
    return {
        "title": templates.PH_CARD_TITLE,
        "subtitle": templates.PH_CARD_SUBTITLE,
        "ph": _fmt(ph),
        "ph_class": plan.ph_class,
        "headline": templates.PH_CARD_HEADLINE.get(plan.ph_class, ""),
        "range": templates.ph_range_text(lower_text, upper_text),
        "advice_title": templates.PH_CARD_ADVICE_TITLE,
        "advice": soil_summary,
        "lab_title": templates.PH_CARD_LAB_TITLE,
        "lab": templates.PH_FIRST_STEP,
    }


def _demo_label(plan: Plan, data: Data) -> str | None:
    """Label of the data file behind the plan, shown before the table (Req 13.6)."""
    if plan.source == "basic_formula":
        return data.basic_formula.get("label")
    if plan.source == "ph_only":
        return data.amendments.get("label")
    return None


def build_advice(
    plan: Plan,
    session: Session,
    data: Data,
    *,
    stub: bool = False,
    model_caller: ModelCaller | None = None,
    deadline: float = DEADLINE_SECONDS,
) -> AdviceMessage:
    """Assemble the advice. `stub=True` adds the demo-data notice.

    With no `model_caller` every text block comes from templates. With one, the model blocks
    are used where they pass their checks, and the template fills any block that does not.
    """
    statuses: dict[str, str] = dict(plan.soil_status)
    rules_label = None
    if plan.source != "ph_only" and not statuses:
        statuses = soil_status(session.values, data.basic_formula)
        if statuses:
            rules_label = data.basic_formula.get("label")

    small_bag_kg = to_decimal(data.limits["small_bag_kg"])
    material = plan.source == "ph_only"
    guide = tuple(templates.per_rai_line(i, small_bag_kg, material=material) for i in plan.items)

    summary = effect = script = None
    if model_caller is not None:
        summary, effect, script = _model_blocks(plan, statuses, model_caller, deadline)

    soil_summary = summary if summary is not None else templates.soil_summary_text(plan, statuses)
    return AdviceMessage(
        demo_label=_demo_label(plan, data),
        table=build_table(plan),
        shop_script=tuple(script if script is not None else template_script(plan)),
        per_rai_guide=guide,
        soil_summary=soil_summary,
        expected_effect=effect if effect is not None else templates.expected_effect_text(plan),
        notices=templates.notices_for(plan, stub=stub, rules_label=rules_label),
        ph_summary=_ph_summary(plan, session, data, soil_summary),
    )
