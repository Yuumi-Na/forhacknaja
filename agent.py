"""หมอดิน AI (Mor Din AI) agent.

Reads a Department of Land Development (DLD) soil sheet photo into 7 soil values
and phrases computed fertilizer numbers as plain village-level Thai.
Spec: .kiro/specs/soil-sheet-to-fertilizer-advice/requirements.md, "Agent design".

Both tools return STUB data from the dicts below. They make no network call,
no Bedrock call and no image analysis. Seed data only, no real personal data.
Run:  uv run agent.py
"""
from strands import Agent, tool
from strands.models import BedrockModel

SYSTEM_PROMPT = (
    "You read soil test sheets and write Thai text, and you do nothing else. "
    "When you are given a photo, read only the values printed on the Department of Land "
    "Development soil sheet: OM, P, K, Ca, Mg, pH and soil texture. Return each value exactly "
    'as printed, and return "unreadable" for any field you cannot read with confidence instead '
    "of guessing. If the photo is not a Department of Land Development soil sheet, or it is "
    "blurry, too dark, cropped or otherwise unreadable, return a reason code (`not_dld_sheet`, "
    "`blurry`, `too_dark`, `cropped` or `unreadable`) and no values. You never do fertilizer "
    "arithmetic, and you never invent, round, convert or change any number. When you are asked "
    "to phrase advice, use only the numbers the system passes to you, copy each kilogram and "
    "baht figure exactly, and add no figure that was not passed in. Write in plain "
    "village-level Thai that a farmer aged 50 or older understands, put each fertilizer on its "
    "own line, and explain any chemical symbol in Thai words. Never say or imply that the "
    "reading or the advice is verified, certified, validated, approved or guaranteed. Label "
    "every price ราคาโดยประมาณ, and say that the advice is a guide based on the values the "
    "farmer confirmed."
)

# STUB: seed fixtures keyed by image reference. Demo numbers, not a real sheet.
STUB_SHEET_READINGS = {
    "demo_sheet_ok": {
        "values": {
            "om": 1.2,
            "p": 8,
            "k": 45,
            "ca": 600,
            "mg": 80,
            "ph": 5.7,
            "soil_texture": "ดินร่วนปนทราย",
        }
    },
    "demo_sheet_partial": {
        "values": {
            "om": 0.9,
            "p": "unreadable",
            "k": 38,
            "ca": 520,
            "mg": "unreadable",
            "ph": 5.4,
            "soil_texture": "ดินทราย",
        }
    },
    "demo_blurry": {"reason_code": "blurry"},
    "demo_not_dld": {"reason_code": "not_dld_sheet"},
}

# STUB: demo prices, not market data. Mirrors the future data/fertilizer_prices.json.
STUB_FERTILIZER_PRICES = {
    "date": "2026-11-01",
    "label": "ราคาตัวอย่างสำหรับทดลอง ไม่ใช่ราคาตลาดจริง",
    "prices_per_kg": {"urea": 20.0, "dap": 28.0, "mop": 24.0},
}


@tool
def read_soil_sheet_values(image_ref: str) -> dict:
    """Read the 7 soil values from an uploaded DLD soil sheet photo (STUB).

    Returns either a "values" object with om, p, k, ca, mg, ph (number or "unreadable")
    and soil_texture (string or "unreadable"), or a "reason_code" when the photo cannot
    be used: not_dld_sheet, blurry, too_dark, cropped or unreadable. Returns seed data
    only. It does not analyze the image.

    Args:
        image_ref: Reference to the uploaded image held in memory, for example "demo_sheet_ok".
    """
    reading = STUB_SHEET_READINGS.get(image_ref.strip())
    if reading is None:
        return {"reason_code": "unreadable"}
    return reading


@tool
def get_fertilizer_prices() -> dict:
    """Get the demo price table for urea (46-0-0), DAP (18-46-0) and MOP (0-0-60) (STUB).

    Returns the price date in ISO format (YYYY-MM-DD), a label saying these are demo
    values, and prices_per_kg in baht per kilogram for urea, dap and mop. These are
    estimated prices, not shop prices.

    Args:
        None. This tool takes no arguments.
    """
    return STUB_FERTILIZER_PRICES


model = BedrockModel(
    model_id="anthropic.claude-sonnet-5",
    region_name="ap-southeast-1",
)

agent = Agent(
    model=model,
    system_prompt=SYSTEM_PROMPT,
    tools=[read_soil_sheet_values, get_fertilizer_prices],
)

if __name__ == "__main__":
    print("หมอดิน AI agent. Type 'exit' to quit.")
    while True:
        text = input("\nYou > ").strip()
        if text.lower() in ("exit", "quit"):
            break
        if text:
            agent(text)
            print()
