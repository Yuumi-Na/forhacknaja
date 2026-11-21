"""หมอดิน AI (Mor Din AI) terminal demo agent.

A DEMO of the "Agent design" in .kiro/specs/soil-sheet-to-fertilizer-advice/requirements.md.
It is not the real system and it does not prove that the requirements are met.

What it does
  - Lab sheet (stub photo reading): uses the fertilizer rate printed on the sheet, no recalculation.
  - Typed soil values: basic fertilizer formula with DEMO rules, or pH-only soil-improvement advice.
  - Asks the field size (rai, ngan, sq wa, sq m, hectare, alone or combined) before any total.
  - Tools do all arithmetic. A figure check replaces any reply that holds a number the tools did not give.

What it does not do
  - No buttons, no web page, no real image reading, no session store, no retry or timing rules.
  - The order of steps is guided by the prompt and by tool checks. It is not a state machine.
  - All numbers below are DEMO values, not agronomy, prices or DLD guidance.

Image names for the stub reader:
  lab sheet:  demo_sheet_ok, demo_sheet_grade (a grade with no price), demo_sheet_partial,
              demo_blurry, demo_not_dld
  pH meter:   demo_meter_ok, demo_meter_blurry

Run:  uv run agent.py     (needs AWS sign-in: aws login)
Type  exit  to quit, and  restart  (or  เริ่มใหม่ ) to start over.
"""
import functools
import re
from decimal import Decimal, ROUND_HALF_UP

from botocore.config import Config as BotocoreConfig
from strands import Agent, tool
from strands.models import BedrockModel

# ---------------------------------------------------------------- AWS settings (aws.md)
MODEL_ID = "anthropic.claude-sonnet-5"
REGION = "ap-southeast-1"
MAX_TOKENS = 1500  # always set explicitly (Bedrock skill rule)


def guard(model_id: str, region: str) -> None:
    """Refuse a Region or model ID the team account does not allow."""
    if region != REGION or model_id.startswith(("global.", "apac.")):
        raise RuntimeError(f"Not allowed: model {model_id!r} in {region!r}. Use {MODEL_ID} in {REGION}.")


# ---------------------------------------------------------------- demo data
DEMO_NOTE = "DEMO values only. Not real prices, rules or guidance."

PRICES = {
    "date": "2026-11-01",
    "label": "ราคาตัวอย่างสำหรับทดลอง ไม่ใช่ราคาตลาดจริง",
    "prices_per_kg": {"urea": 20.0, "dap": 28.0, "mop": 24.0, "agri_lime": 3.0},  # "15-15-15" has no price on purpose
}
CANE = {
    "date": "2026-11-01",
    "label": "ราคาตัวอย่างสำหรับทดลอง ไม่ใช่ราคาจริง",
    "unit": "THB per tonne of cane",
    "central_price_thb": 1000,
    "regional_prices_thb": {"northeast": 980, "north": 1010, "central": 1020, "east": 1000},
}
LIMITS = {
    "ranges": {"ph": (3.0, 10.0), "om": (0.0, 20.0), "p": (0.0, 500.0), "k": (0.0, 1000.0),
               "ca": (0.0, 10000.0), "mg": (0.0, 2000.0)},
    "textures": ["ดินทราย", "ดินร่วนปนทราย", "ดินร่วน", "ดินเหนียว"],
    "rate_max_kg_per_rai": 200,
    "small_bag_kg": 5,
}
REQUIRED_FOR_FORMULA = ("om", "p", "k")
# Targets fall as the soil level rises. (upper bound, exclusive; None = no bound) -> kg per rai of nutrient.
TARGETS = {
    "n": ("om", [(1.0, 12), (2.0, 8), (None, 4)]),
    "p2o5": ("p", [(10, 8), (20, 4), (30, 2), (None, 0)]),
    "k2o": ("k", [(40, 10), (80, 6), (None, 0)]),
}
MAX_KG_PER_RAI = {"urea": 40, "dap": 30, "mop": 25}
STATUS_BANDS = {"om": (1.0, 2.0, 3.0), "p": (10, 20, 30), "k": (40, 80, 120),
                "ca": (200, 500, 1000), "mg": (30, 60, 120)}
TEXTURE_STATUS = {"ดินทราย": "low", "ดินร่วนปนทราย": "fair", "ดินร่วน": "good", "ดินเหนียว": "fair"}
AMENDMENTS = {
    "acidic_below": 6.0,
    "alkaline_above": 6.5,
    "materials": {"acidic": ("agri_lime", 100, 400), "balanced": None, "alkaline": None},  # (key, kg/rai, max)
}

SHEETS = {
    "demo_sheet_ok": {
        "values": {"om": 1.2, "p": 8, "k": 45, "ca": 600, "mg": 80, "ph": 5.7, "soil_texture": "ดินร่วนปนทราย"},
        "recs": [{"fertilizer": "urea", "rate_kg_per_rai": 20.98}, {"fertilizer": "mop", "rate_kg_per_rai": 12}],
    },
    "demo_sheet_grade": {
        "values": {"om": 0.9, "p": 6, "k": 38, "ca": 520, "mg": 70, "ph": 5.4, "soil_texture": "ดินทราย"},
        "recs": [{"fertilizer": "15-15-15", "rate_kg_per_rai": 30}],
    },
    "demo_sheet_partial": {
        "values": {"om": 0.9, "p": "unreadable", "k": 38, "ca": 520, "mg": "unreadable", "ph": 5.4,
                   "soil_texture": "ดินทราย"},
        "recs": [{"fertilizer": "urea", "rate_kg_per_rai": "unreadable"}],
    },
    "demo_blurry": {"reason": "blurry"},
    "demo_not_dld": {"reason": "not_dld_sheet"},
}
METERS = {"demo_meter_ok": {"ph": 5.4}, "demo_meter_blurry": {"reason": "blurry"}}

NAMES = {
    "urea": ("ยูเรีย 46-0-0", "Urea 46-0-0"),
    "dap": ("ดีเอพี 18-46-0", "DAP 18-46-0"),
    "mop": ("โพแทส 0-0-60", "Potash 0-0-60"),
    "agri_lime": ("ปูนปรับปรุงดิน", "Agricultural lime"),
}
DESCRIPTIONS = {
    "urea": ("เพิ่มไนโตรเจน ช่วยให้ใบและลำเจริญเติบโต", "Adds nitrogen for leaf and stalk growth"),
    "dap": ("เพิ่มฟอสฟอรัสและไนโตรเจน ช่วยการแตกรากและแตกกอ", "Adds phosphorus and nitrogen for roots and tillering"),
    "mop": ("เพิ่มโพแทสเซียม ช่วยให้ลำอ้อยแข็งแรง", "Adds potassium for a stronger stalk"),
    "agri_lime": ("ลดความเป็นกรดของดิน", "Lowers soil acidity"),
}
DEFAULT_DESCRIPTION = ("ปุ๋ยตามคำแนะนำในใบตรวจดิน", "Fertilizer as recommended on your soil sheet")
TEXT = {
    "th": {
        "columns": ["ชื่อปุ๋ย", "กก./ไร่", "รวม (กก.)", "ราคารวมโดยประมาณ (บาท)", "คำอธิบาย"],
        "heading": "แผนสำหรับ {area} ไร่",
        "total": "รวม",
        "no_price": "ไม่มีราคา",
        "partial": "ราคารวมนับเฉพาะรายการที่มีราคา",
        "per_rai": "{name}: ถ้าปุ๋ยถุงละ {bag} กก. ใช้หว่านประมาณ {bags} ถุงต่อ 1 ไร่ (ประมาณ {rate} กก.)",
        "per_rai_less": "{name}: ถ้าปุ๋ยถุงละ {bag} กก. ใช้หว่านไม่ถึงครึ่งถุงต่อ 1 ไร่ (ประมาณ {rate} กก.)",
        "price": "ราคาทั้งหมดเป็นราคาโดยประมาณ (บาท) อ้างอิงวันที่ {date} อาจต่างจากราคาที่ร้านจริง",
        "guide": "คำแนะนำนี้เป็นแนวทางจากค่าที่คุณยืนยันหรือพิมพ์ ไม่ใช่การรับรองผล",
        "demo_label": "ผลนี้ใช้กฎตัวอย่างสำหรับทดลอง ไม่ใช่คำแนะนำจริงของกรมพัฒนาที่ดิน ห้ามใช้ตัดสินใจซื้อปุ๋ยจริง",
        "first_step": "นี่เป็นเพียงขั้นแรก ควรตรวจดินจากแล็บเพิ่มเติมเพื่อความแม่นยำ",
        "acidic": "ดินเป็นกรด", "balanced": "ดินสมดุล", "alkaline": "ดินเป็นด่าง",
        "no_material": "ตอนนี้ยังไม่มีวัสดุปรับปรุงดินที่แนะนำสำหรับค่านี้",
    },
    "en": {
        "columns": ["Name", "kg/rai", "Total kg", "Estimated total price (THB)", "Description"],
        "heading": "Plan for {area} rai",
        "total": "Total",
        "no_price": "no price available",
        "partial": "The total counts only items that have a price",
        "per_rai": "{name}: if your fertilizer comes in {bag} kg bags, broadcast about {bags} bags on 1 rai (about {rate} kg)",
        "per_rai_less": "{name}: if your fertilizer comes in {bag} kg bags, broadcast less than half a bag on 1 rai (about {rate} kg)",
        "price": "All prices are estimated prices in baht (THB) as of {date} and may differ from the shop price",
        "guide": "This advice is a guide based on the values you confirmed or typed. It is not a guarantee",
        "demo_label": "This result uses demo rules, not real DLD guidance. Do not use it for a real fertilizer purchase",
        "first_step": "This is only a first step. Please also get a lab soil test for accuracy",
        "acidic": "The soil is acidic", "balanced": "The soil is balanced", "alkaline": "The soil is alkaline",
        "no_material": "There is no soil-improvement material advised for this value right now",
    },
}

# ---------------------------------------------------------------- session (single user in the terminal)
SESSION = {}
ALLOWED = set()  # numbers the tools gave in this turn, for the figure check


def reset_session() -> None:
    SESSION.clear()
    SESSION.update(source=None, values={}, recs=[], confirmed=False, area_rai=None, read_fail=0)


reset_session()


# ---------------------------------------------------------------- number helpers
def D(x) -> Decimal:
    return Decimal(str(x))


def rhu(x: Decimal, places: int = 0) -> Decimal:
    """Round half up."""
    return x.quantize(Decimal(1).scaleb(-places), rounding=ROUND_HALF_UP)


def fmt(x: Decimal) -> str:
    s = f"{x:f}"
    return s.rstrip("0").rstrip(".") if "." in s else s


def iso_to_dmy(iso: str) -> str:
    y, m, d = iso.split("-")
    return f"{d}-{m}-{y}"


# ---------------------------------------------------------------- field size
UNIT_RAI = {"rai": D(1), "ngan": D("0.25"), "sqwa": D("0.0025"), "sqm": D("0.000625"), "ha": D("6.25")}
_UNIT_PATTERNS = [
    (r"ตารางเมตร|ตร\.\s*ม\.?|square\s*met(?:re|er)s?|sq\.?\s*m(?![a-z])|m2|m²", " sqm "),
    (r"ตารางวา|ตร\.\s*ว\.?|square\s*wa|sq\.?\s*wa", " sqwa "),
    (r"เฮกตาร์|hectares?|\bha\b", " ha "),
    (r"ไร่|\brai\b", " rai "),
    (r"งาน|\bngan\b", " ngan "),
]
_AREA_PART = re.compile(r"(\d+(?:\.\d+)?)\s*(sqm|sqwa|rai|ngan|ha)?")


class AreaError(ValueError):
    pass


def parse_area(text: str) -> Decimal:
    """Turn a field size answer into rai. A bare number is rai. Raises AreaError."""
    s = text.lower().replace(",", "")
    for pattern, token in _UNIT_PATTERNS:
        s = re.sub(pattern, token, s)
    parts = list(_AREA_PART.finditer(s))
    if re.search(r"[-−]\s*\d", s):
        raise AreaError("must not be negative")
    if not parts or re.search(r"\w", _AREA_PART.sub("", s)):
        raise AreaError("not understood")
    if len(parts) > 1 and any(p.group(2) is None for p in parts):
        raise AreaError("every number needs a unit when there are several")
    units = [p.group(2) or "rai" for p in parts]
    if len(set(units)) != len(units):
        raise AreaError("a unit is repeated")
    area = rhu(sum(D(p.group(1)) * UNIT_RAI[u] for p, u in zip(parts, units)), 4)
    if area <= 0:
        raise AreaError("must be more than 0")
    return area


# ---------------------------------------------------------------- calculators (deterministic)
def check_range(field: str, value) -> bool:
    lo, hi = LIMITS["ranges"][field]
    return isinstance(value, (int, float)) and not isinstance(value, bool) and lo <= value <= hi


def status_of(field: str, value) -> str:
    t0, t1, t2 = STATUS_BANDS[field]
    return "needs_action" if value < t0 else "low" if value < t1 else "fair" if value < t2 else "good"


def classify_ph(ph: float) -> str:
    return "acidic" if ph < AMENDMENTS["acidic_below"] else "alkaline" if ph > AMENDMENTS["alkaline_above"] else "balanced"


def soil_status(values: dict) -> dict:
    out = {f: status_of(f, values[f]) for f in STATUS_BANDS if values.get(f) is not None}
    if values.get("ph") is not None:
        out["ph"] = {"acidic": "low", "balanced": "good", "alkaline": "low"}[classify_ph(values["ph"])]
    if values.get("soil_texture") in TEXTURE_STATUS:
        out["soil_texture"] = TEXTURE_STATUS[values["soil_texture"]]
    return out


def _target(nutrient: str, values: dict) -> Decimal:
    field, bands = TARGETS[nutrient]
    v = values[field]
    for upper, target in bands:
        if upper is None or v < upper:
            return D(target)
    return D(0)


def basic_formula(values: dict) -> dict:
    """Urea, DAP and MOP in kg per rai from typed soil values, with DEMO rules."""
    dap_raw = _target("p2o5", values) / D("0.46")
    urea_raw = max(D(0), _target("n", values) - dap_raw * D("0.18")) / D("0.46")
    mop_raw = _target("k2o", values) / D("0.60")
    raw = {"urea": urea_raw, "dap": dap_raw, "mop": mop_raw}
    return {k: min(rhu(v), D(MAX_KG_PER_RAI[k])) for k, v in raw.items()}


def compute_item(key: str, rate: Decimal, area_rai: Decimal) -> dict:
    total_kg = rhu(rate * area_rai, 1)
    price = PRICES["prices_per_kg"].get(key)
    bags = rhu(rate / D(LIMITS["small_bag_kg"]) * 2) / 2
    return {
        "key": key,
        "rate_kg_per_rai": rate,
        "total_kg": total_kg,
        "total_price_thb": None if price is None else rhu(total_kg * D(price)),
        "script_kg": int(rhu(total_kg)),
        "small_bags_per_rai": bags,
    }


# ---------------------------------------------------------------- output text (fixed text, no model)
def _i(lang: str) -> int:
    return 0 if lang == "th" else 1


def build_table(items: list, area_rai: Decimal, lang: str) -> str:
    t, i = TEXT[lang], _i(lang)
    lines = [t["heading"].format(area=fmt(area_rai)), " | ".join(t["columns"])]
    priced = [x["total_price_thb"] for x in items if x["total_price_thb"] is not None]
    for x in items:
        name = NAMES.get(x["key"], (x["key"], x["key"]))[i]
        desc = DESCRIPTIONS.get(x["key"], DEFAULT_DESCRIPTION)[i]
        price = t["no_price"] if x["total_price_thb"] is None else f"{int(x['total_price_thb']):,}"
        lines.append(f"{name} | {fmt(x['rate_kg_per_rai'])} | {x['total_kg']:.1f} | {price} | {desc}")
    total = f"{int(sum(priced)):,}" if priced else "-"
    lines.append(f"{t['total']} | | | {total} | " + (t["partial"] if len(priced) < len(items) else ""))
    return "\n".join(lines)


def per_rai_lines(items: list, lang: str) -> list:
    t, i = TEXT[lang], _i(lang)
    out = []
    for x in items:
        bags = x["small_bags_per_rai"]
        name = NAMES.get(x["key"], (x["key"], x["key"]))[i]
        template = t["per_rai_less"] if bags == 0 else t["per_rai"]
        out.append(template.format(name=name, bag=LIMITS["small_bag_kg"], bags=fmt(bags),
                                   rate=fmt(x["rate_kg_per_rai"])))
    return out


def _plain(x):
    """Make Decimals JSON friendly."""
    if isinstance(x, Decimal):
        return float(x)
    if isinstance(x, dict):
        return {k: _plain(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [_plain(v) for v in x]
    return x


# ---------------------------------------------------------------- figure check
_NUM = re.compile(r"\d[\d,]*(?:\.\d+)?")
_FIGURE = re.compile(r"(\d[\d,]*(?:\.\d+)?)\s*(กก\.?|กิโลกรัม|กิโล|kg|บาท|thb|baht|ไร่|rai|ถุง|bags?)", re.I)


def _collect(obj) -> None:
    if isinstance(obj, bool):
        return
    if isinstance(obj, (int, float, Decimal)):
        ALLOWED.add(D(obj))
    elif isinstance(obj, str):
        ALLOWED.update(D(m.replace(",", "")) for m in _NUM.findall(obj))
    elif isinstance(obj, dict):
        for v in obj.values():
            _collect(v)
    elif isinstance(obj, (list, tuple)):
        for v in obj:
            _collect(v)


def unknown_figures(text: str) -> list:
    """Figures with a unit (kg, baht, rai, bag) that no tool gave in this turn."""
    ok = ALLOWED | {D(1)}
    return [m.group(0) for m in _FIGURE.finditer(text) if D(m.group(1).replace(",", "")) not in ok]


def _track(fn):
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        result = _plain(fn(*args, **kwargs))
        _collect(result)
        return result
    return wrapper


# ---------------------------------------------------------------- tools
RETAKE_TIPS = ["put the sheet or meter flat in daylight", "hold the phone steady and straight above it",
               "fill the frame with the sheet or display", "avoid shadow and glare",
               "make sure the numbers are sharp"]


def _retake(reason_or_parts, not_dld: bool = False) -> dict:
    SESSION["read_fail"] += 1
    return {"status": "not_dld_sheet" if not_dld else "retake_needed", "unreadable": reason_or_parts,
            "retake_tips": RETAKE_TIPS, "offer_manual_entry": SESSION["read_fail"] >= 2 or not_dld}


@tool
@_track
def read_soil_sheet_values(image_ref: str) -> dict:
    """Read a DLD soil sheet photo (STUB). Returns the 7 soil values and the fertilizer formula and rate
    printed on the sheet. Nothing is confirmed yet: ask the farmer to confirm or correct before going on.
    If the photo cannot be read, the result says which parts failed and gives photo tips.

    Args:
        image_ref: Name of the uploaded image, for example "demo_sheet_ok".
    """
    reading = SHEETS.get(image_ref.strip())
    if reading is None or "reason" in reading:
        reason = (reading or {}).get("reason", "unreadable")
        return _retake([reason], not_dld=reason == "not_dld_sheet")
    values = dict(reading["values"])
    unreadable = []
    for f in LIMITS["ranges"]:
        if not check_range(f, values.get(f)):
            values[f] = "unreadable"
            unreadable.append(f)
    if values.get("soil_texture") not in LIMITS["textures"]:
        values["soil_texture"] = "unreadable"
        unreadable.append("soil_texture")
    recs = [dict(r) for r in reading["recs"]]
    for r in recs:
        if not isinstance(r["rate_kg_per_rai"], (int, float)) or r["rate_kg_per_rai"] <= 0:
            r["rate_kg_per_rai"] = "unreadable"
            unreadable.append(f"rate of {r['fertilizer']}")
    if not recs:
        unreadable.append("recommended formula and rate")
    if unreadable:
        return _retake(unreadable)
    SESSION.update(source="lab_sheet", values=values, recs=recs, confirmed=False, area_rai=None, read_fail=0)
    warnings = [f"check the rate of {r['fertilizer']} against the sheet" for r in recs
                if r["rate_kg_per_rai"] > LIMITS["rate_max_kg_per_rai"]]
    return {"status": "values_read", "values": values, "sheet_recommendations": recs, "warnings": warnings,
            "note": "Read by AI and may be wrong. Ask the farmer to confirm or correct."}


@tool
@_track
def read_ph_meter(image_ref: str) -> dict:
    """Read the pH from a photo of a soil pH meter display (STUB). Nothing is confirmed yet.

    Args:
        image_ref: Name of the uploaded image, for example "demo_meter_ok".
    """
    reading = METERS.get(image_ref.strip())
    if reading is None or "reason" in reading or not check_range("ph", reading.get("ph")):
        return _retake([(reading or {}).get("reason", "unreadable")])
    SESSION.update(source="ph_meter", values={"ph": reading["ph"]}, recs=[], confirmed=False,
                   area_rai=None, read_fail=0)
    return {"status": "values_read", "values": {"ph": reading["ph"]},
            "note": "Read by AI and may be wrong. Ask the farmer to confirm or correct."}


@tool
@_track
def confirm_values(corrections: dict | None = None) -> dict:
    """Record that the farmer confirmed the values read from a photo. Call this ONLY after the farmer
    says yes. Optional corrections use soil field names (om, p, k, ca, mg, ph, soil_texture) or
    "rate:<fertilizer>" for a sheet rate, for example {"p": 10, "rate:urea": 18}.

    Args:
        corrections: Values the farmer corrected, or None.
    """
    if SESSION["source"] not in ("lab_sheet", "ph_meter"):
        return {"status": "error", "message": "There are no photo values to confirm."}
    rejected = {}
    for key, val in (corrections or {}).items():
        if key.startswith("rate:"):
            rec = next((r for r in SESSION["recs"] if r["fertilizer"] == key[5:]), None)
            if rec and isinstance(val, (int, float)) and 0 < val <= LIMITS["rate_max_kg_per_rai"]:
                rec["rate_kg_per_rai"] = val
                continue
            rejected[key] = f"must be more than 0 and at most {LIMITS['rate_max_kg_per_rai']} kg per rai"
        elif key == "soil_texture" and val in LIMITS["textures"]:
            SESSION["values"][key] = val
        elif key in LIMITS["ranges"] and check_range(key, val):
            SESSION["values"][key] = val
        else:
            rejected[key] = "not accepted"
    if rejected:
        return {"status": "rejected", "rejected": rejected, "values": SESSION["values"],
                "sheet_recommendations": SESSION["recs"]}
    SESSION["confirmed"] = True
    return {"status": "confirmed", "values": SESSION["values"], "sheet_recommendations": SESSION["recs"],
            "next": "ask the field size"}


@tool
@_track
def enter_manual_values(om: float | None = None, p: float | None = None, k: float | None = None,
                        ca: float | None = None, mg: float | None = None, ph: float | None = None) -> dict:
    """Record soil values the farmer typed. Pass only the values the farmer gave. Values outside the valid
    range are rejected with the accepted range. Typed values need no separate confirmation. Show the
    accepted values back to the farmer and then ask the field size.

    Args:
        om: Organic matter, percent.
        p: Phosphorus, mg/kg.
        k: Potassium, mg/kg.
        ca: Calcium, mg/kg.
        mg: Magnesium, mg/kg.
        ph: Soil pH.
    """
    if SESSION["source"] != "manual":
        reset_session()
        SESSION["source"] = "manual"
    accepted, rejected = {}, {}
    for f, v in (("om", om), ("p", p), ("k", k), ("ca", ca), ("mg", mg), ("ph", ph)):
        if v is None:
            continue
        if check_range(f, v):
            accepted[f] = v
        else:
            rejected[f] = f"accepted range {LIMITS['ranges'][f][0]} to {LIMITS['ranges'][f][1]}"
    SESSION["values"].update(accepted)
    SESSION["confirmed"] = bool(SESSION["values"])
    have = SESSION["values"]
    missing = [f for f in REQUIRED_FOR_FORMULA if f not in have]
    route = "ph_only" if set(have) == {"ph"} else "basic_formula" if not missing else "needs_more_values"
    out = {"status": "ok", "accepted": accepted, "rejected": rejected, "all_values": have, "route": route}
    if route == "needs_more_values":
        out["missing_required"] = missing
        out["ph_only_possible"] = "ph" in have
    return out


@tool
@_track
def set_field_size(answer: str) -> dict:
    """Read the farmer's field size answer and store it in rai. Accepts rai, ngan, square wa, square metres
    and hectares, alone or combined ("3 ไร่ 2 งาน"). A bare number means rai. Never convert units yourself.

    Args:
        answer: The farmer's answer exactly as typed.
    """
    try:
        area = parse_area(answer)
    except AreaError as e:
        return {"status": "invalid", "reason": str(e), "example": "5 ไร่ / 3 ไร่ 2 งาน / 2 เฮกตาร์"}
    SESSION["area_rai"] = area
    return {"status": "ok", "area_rai": area, "echo": f"{answer.strip()} = {fmt(area)} rai"}


@tool
@_track
def build_plan(language: str = "th", ph_only: bool = False) -> dict:
    """Build the recommendation with totals and estimated prices. All numbers come from this tool. It refuses
    until photo values are confirmed (or values were typed) and the field size is set. Print `table_text`
    exactly, then use `items[].script_kg`, `area_rai`, `per_rai_guide` and `notices` for the rest of the reply.

    Args:
        language: "th" if the farmer wrote Thai, "en" if English.
        ph_only: True only when the farmer chose to continue with pH-only advice while other values are missing.
    """
    lang = "en" if language.lower().startswith("en") else "th"
    t = TEXT[lang]
    if SESSION["source"] is None or not SESSION["confirmed"]:
        return {"status": "error", "message": "Values are not confirmed yet. Ask the farmer first."}
    if SESSION["area_rai"] is None:
        return {"status": "error", "message": "The field size is not set. Ask the farmer for it first."}
    area, values = SESSION["area_rai"], SESSION["values"]
    notices = [t["price"].format(date=iso_to_dmy(PRICES["date"])), t["guide"]]
    out = {"status": "ok", "language": lang, "area_rai": area, "small_bag_kg": LIMITS["small_bag_kg"],
           "demo_label": None, "ph_class": None}

    if SESSION["source"] == "lab_sheet":
        out["source"] = "sheet"
        items = [compute_item(r["fertilizer"], D(r["rate_kg_per_rai"]), area) for r in SESSION["recs"]]
        out["soil_status"] = soil_status(values)
    elif SESSION["source"] == "manual" and not ph_only and all(f in values for f in REQUIRED_FOR_FORMULA):
        out["source"] = "basic_formula"
        out["demo_label"] = t["demo_label"]
        items = [compute_item(k, rate, area) for k, rate in basic_formula(values).items() if rate > 0]
        out["soil_status"] = soil_status(values)
    elif "ph" in values and (SESSION["source"] == "ph_meter" or ph_only or set(values) == {"ph"}):
        out["source"] = "ph_only"
        out["demo_label"] = t["demo_label"]
        cls = classify_ph(values["ph"])
        out["ph_class"] = cls
        out["ph_class_text"] = t[cls]
        material = AMENDMENTS["materials"][cls]
        items = [compute_item(material[0], D(material[1]), area)] if material else []
        if not material:
            notices.append(t["no_material"])
        notices.append(t["first_step"])
        out["soil_status"] = soil_status({"ph": values["ph"]})
    else:
        missing = [f for f in REQUIRED_FOR_FORMULA if f not in values]
        return {"status": "needs_more_values", "missing_required": missing, "ph_only_possible": "ph" in values}

    out["items"] = items
    out["table_text"] = build_table(items, area, lang) if items else None
    out["per_rai_guide"] = per_rai_lines(items, lang)
    out["notices"] = notices
    return out


GUIDE = {
    "th": [
        "วิธีใช้หมอดิน AI",
        "1. ส่งรูปใบตรวจดินของกรมพัฒนาที่ดิน หรือรูปหน้าจอเครื่องวัด pH ถ่ายให้ชัด",
        "2. หรือพิมพ์ค่าดินเอง เช่น OM 1.2 P 8 K 45 pH 5.7 หรือพิมพ์แค่ pH ก็ได้",
        "3. ถ้าส่งรูป ให้ตรวจค่าที่ AI อ่านได้ ถ้าไม่ตรงให้บอกค่าที่ถูกต้อง",
        "4. บอกขนาดพื้นที่ปลูก ตอบเป็น ไร่ งาน ตารางวา ตารางเมตร หรือเฮกตาร์ก็ได้ เช่น 5 ไร่ หรือ 3 ไร่ 2 งาน",
        "5. ระบบจะตอบเป็นตารางสรุป ได้แก่ ชื่อปุ๋ย ปริมาณต่อไร่ ปริมาณรวม และราคารวมโดยประมาณ (บาท) "
        "พร้อมประโยคสั้น ๆ ไว้บอกร้านปุ๋ย",
        "6. ถามต่อได้ เช่น ราคาอ้อย หรือคำถามเรื่องปุ๋ยและดิน",
        "7. อยากเริ่มใหม่ พิมพ์ \"เริ่มใหม่\"",
        "เคล็ดลับถ่ายรูป: วางใบตรวจดินหรือเครื่องวัดให้ราบ ถ่ายในที่สว่าง ถือมือให้นิ่งและถ่ายตรงจากด้านบน "
        "ให้ภาพเต็มกรอบ หลีกเลี่ยงเงาและแสงสะท้อน และให้ตัวเลขคมชัด",
    ],
    "en": [
        "How to use หมอดิน AI",
        "1. Send a photo of your DLD soil sheet, or a photo of the pH meter display. Take it clearly.",
        "2. Or type the soil values yourself, for example OM 1.2 P 8 K 45 pH 5.7. Typing only the pH is fine too.",
        "3. If you sent a photo, check the values the AI read and tell me the right value if one is wrong.",
        "4. Tell me the size of your field. You can answer in rai, ngan, square wa, square metres or hectares, "
        "for example 5 rai or 3 rai 2 ngan.",
        "5. I answer with a summary table: fertilizer name, amount per rai, total amount and estimated total price "
        "(THB), plus a short sentence you can say at the fertilizer shop.",
        "6. You can keep asking, for example about cane prices, or about fertilizer and soil.",
        "7. To start over, type \"restart\".",
        "Photo tips: put the sheet or meter flat in daylight, hold the phone steady and straight above it, "
        "fill the frame, avoid shadow and glare, and make sure the numbers are sharp.",
    ],
}
DEMO_GUIDE_NOTE = {
    "th": "ในเดโมนี้ ให้พิมพ์ชื่อรูปแทนการส่งรูปจริง เช่น demo_sheet_ok หรือ demo_meter_ok",
    "en": "In this demo, type an image name instead of sending a real photo, for example demo_sheet_ok or demo_meter_ok.",
}


@tool
@_track
def get_usage_guide(language: str = "th") -> dict:
    """Get the step-by-step guide on how to use this tool. Use it whenever the farmer asks how to use the tool,
    what it can do, or what to do next. Print the guide lines as given.

    Args:
        language: "th" if the farmer wrote Thai, "en" if English.
    """
    lang = "en" if language.lower().startswith("en") else "th"
    return {"guide": GUIDE[lang], "demo_note": DEMO_GUIDE_NOTE[lang]}


@tool
@_track
def get_fertilizer_prices() -> dict:
    """Get the demo fertilizer price table: date, a demo label and baht per kg for each fertilizer."""
    return PRICES


@tool
@_track
def get_cane_prices() -> dict:
    """Get the demo central reference cane price and the prices by region, in baht, with the date."""
    return CANE


TOOLS = [read_soil_sheet_values, read_ph_meter, confirm_values, enter_manual_values, set_field_size,
         build_plan, get_usage_guide, get_fertilizer_prices, get_cane_prices]

# ---------------------------------------------------------------- prompt
SYSTEM_PROMPT = """\
You are หมอดิน AI, a friendly helper for Thai sugarcane farmers. This is a DEMO.

Reply in the language the farmer wrote in (Thai to Thai, English to English). Use plain, friendly words a
farmer aged 50 or older understands, and avoid hard technical terms. Explain any chemical symbol in plain words.

What the farmer can do: send a soil sheet photo, send a pH meter photo, type soil values (OM, P, K, Ca, Mg, pH)
or only a pH, ask for cane prices, ask how to use the tool, or ask questions. In this terminal demo a photo is
given as an image name, for example "demo_sheet_ok".

Steps, in this order:
1. Photo: call read_soil_sheet_values or read_ph_meter. Show what was read, including the fertilizer formula and
   rate printed on the sheet, say it was read by AI and may be wrong, and ask the farmer to confirm or correct.
   Call confirm_values only after the farmer says yes (pass corrections if they gave any).
   If it could not be read, name the parts that failed, give the retake tips, and ask for a clearer photo.
   If offer_manual_entry is true, also offer typing the values. Never guess an unreadable value or a rate.
2. Typed values: call enter_manual_values with only what the farmer gave. Show the accepted values back.
   If route is needs_more_values, name the missing values and, if ph_only_possible, offer pH-only advice.
3. Always ask the field size before any total or price. Call set_field_size with the answer as typed.
   Never convert units or assume a size. If it is invalid, ask again with the example.
4. Then call build_plan (language = the farmer's language). Never calculate anything yourself.

Reply format after build_plan:
- If demo_label is not null, say it first.
- Print table_text exactly as given.
- Write a shop script of at most 3 sentences, in the farmer's language, the way a farmer speaks at the shop:
  name each fertilizer and say "about <script_kg> kg" and the field size (area_rai). Give no number of bags
  and no bag size in the script. Use only script_kg and area_rai as numbers.
- Print the lines in per_rai_guide as given.
- One or two short sentences saying what the advice should do for cane yield. Say "should help". Give no yield
  number and no promise.
- Print the notices.
For pH-only, also say whether the soil is acidic, alkaline or balanced (ph_class_text) and that this is a first step.

Rules:
- Every number about fertilizer, soil improvement, amount, price or cane price must come from a tool result in
  this conversation. If you have none, say you are not sure and say what the farmer can send or type.
- Prices are estimated prices in baht (THB). Say so.
- Never say or imply that the reading or the advice is verified, certified, validated, approved or guaranteed.
- Never mention a survey of 50 farmers.
- For cane prices call get_cane_prices. For fertilizer prices call get_fertilizer_prices.
- How-to questions ("how do I use this", "what can you do", "วิธีใช้", "ทำอะไรได้บ้าง", or when the farmer seems lost,
  or says only hello): call get_usage_guide (language = the farmer's language), print the guide lines as given,
  then print the demo_note, then ask what the farmer wants to do first. Never answer a how-to question with
  "I am not sure". The guide is a tool result, so its numbers are fine to use.
"""

SAFE_FALLBACK = {
    "th": "ขออภัย ผมไม่แน่ใจตัวเลขในคำตอบนี้ ขอให้ถามใหม่หรือพิมพ์ค่าอีกครั้งนะครับ",
    "en": "Sorry, I am not sure about the numbers in that answer. Please ask again or type the values again.",
}


def make_agent() -> Agent:
    guard(MODEL_ID, REGION)
    model = BedrockModel(
        model_id=MODEL_ID,
        region_name=REGION,
        max_tokens=MAX_TOKENS,
        boto_client_config=BotocoreConfig(connect_timeout=5, read_timeout=60,
                                          retries={"max_attempts": 2, "mode": "standard"}),
    )
    return Agent(model=model, system_prompt=SYSTEM_PROMPT, tools=TOOLS, callback_handler=None)


def main() -> None:
    agent = make_agent()
    print("หมอดิน AI demo agent. Type 'exit' to quit, 'restart' to start over.")
    print("This is a demo. AI reading accuracy has not been validated. All numbers are demo values.")
    while True:
        text = input("\nYou > ").strip()
        if text.lower() in ("exit", "quit"):
            break
        if text.lower() == "restart" or text == "เริ่มใหม่":
            reset_session()
            agent.messages.clear()
            print("Started over.")
            continue
        if not text:
            continue
        ALLOWED.clear()
        reply = str(agent(text))
        bad = unknown_figures(reply)
        if bad:
            print(f"[figure check] replaced a reply with figures no tool gave: {bad}")
            reply = SAFE_FALLBACK["th" if re.search(r"[ก-๙]", text) else "en"]
        print(f"\n{reply}")


if __name__ == "__main__":
    main()
