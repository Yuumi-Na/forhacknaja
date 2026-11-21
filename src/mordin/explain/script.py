"""Shop script: template script, the model draft type and its check (Req 12)."""

from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel, Field

from mordin.explain import figures, messages, templates
from mordin.fertilizer.plan import Plan

MAX_SENTENCES = 3


class ScriptDraft(BaseModel):
    """A model-written shop script: 1 to 3 sentences."""

    sentences: list[str] = Field(min_length=1, max_length=MAX_SENTENCES)


def check_script(draft: ScriptDraft, plan: Plan) -> list[str]:
    """Return problems with a draft (empty list means it passes), Req 12.4.

    At most 3 non-empty sentences. Every `script_kg` and the `area_rai` appear exactly. No bag
    count or size. No other figure with a weight, money or area unit.
    """
    problems: list[str] = []
    sentences = [s.strip() for s in draft.sentences]
    if not 1 <= len(sentences) <= MAX_SENTENCES or not all(sentences):
        problems.append("sentence_count")
    text = " ".join(sentences)
    found = figures.find_figures(text)

    if "ถุง" in text or any(f.kind == figures.BAG for f in found):
        problems.append("bag_figure")

    weights = {f.value for f in found if f.kind == figures.WEIGHT}
    areas = {f.value for f in found if f.kind == figures.AREA}
    for item in plan.items:
        if Decimal(item.script_kg) not in weights:
            problems.append(f"missing_script_kg:{item.key}")
    if Decimal(plan.area_rai) not in areas:
        problems.append("missing_area_rai")

    allowed = {
        figures.WEIGHT: [i.script_kg for i in plan.items],
        figures.AREA: [plan.area_rai],
    }
    if figures.check_figures(text, allowed):
        problems.append("extra_figure")
    problems.extend(f"wording:{w}" for w in figures.check_wording(text))
    return problems


def template_script(plan: Plan) -> list[str]:
    """At most 3 sentences for any number of items.

    Sentence 1 gives area_rai. Sentence 2 names every item with its script_kg. Sentence 3 asks
    the shop for help. It gives no bag count and no bag size. With no items it says nothing
    needs to be bought.
    """
    area = templates.SCRIPT_AREA.format(area=templates.fmt_decimal(plan.area_rai))
    if plan.items:
        parts = [
            templates.SCRIPT_ITEM.format(name=messages.item_name(i.key), kg=i.script_kg)
            for i in plan.items
        ]
        joined = parts[0] if len(parts) == 1 else ", ".join(parts[:-1]) + " และ " + parts[-1]
        middle = templates.SCRIPT_ITEMS.format(items=joined)
    else:
        middle = templates.SCRIPT_NONE
    return [area, middle, templates.SCRIPT_ASK][:MAX_SENTENCES]
