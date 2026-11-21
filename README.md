# หมอดิน AI (Mor Din AI) - local demo

A local web demo that turns a soil test result into fertilizer advice for sugarcane farmers. It runs on your computer without LINE. The UI is Thai only.

## Run

```
uv sync
uv run mordin
```

Then open http://127.0.0.1:8000 in a browser.

Run the tests:

```
uv run pytest
```

## Vision stub switch

- `MORDIN_VISION_STUB=1`: the app reads sample fixtures from `tests/fixtures` and makes no Bedrock call. No AWS sign-in needed.
- Default (off): the app calls Amazon Bedrock with model `anthropic.claude-sonnet-5` in `ap-southeast-1`. Sign in first with `aws login`.

PowerShell example:

```
$env:MORDIN_VISION_STUB = "1"
uv run mordin
```

## Flows

- **A. Lab sheet photo:** the AI reads the soil values and the fertilizer formula and rate printed on the sheet. The farmer confirms or edits them, then gives the field size. The sheet's rate is multiplied by the field size, not recalculated.
- **B. Manual, full values:** the farmer types soil values. The basic sugarcane formula gives the rate, then the totals for the field.
- **C. Manual, pH only:** the pH class (acidic, balanced, alkaline) gives a first-step soil improvement material and amount. A lab soil test is recommended.

## Warnings

- **Demo data only.** Fertilizer prices, the basic formula rules and the soil amendment table are placeholder demo values. They are not real DLD guidance. Do not use them for real purchase decisions.
- **AI reading accuracy has not been validated** against the lab sheet test set.

## Other

- `agent.py` is a separate starter demo agent, not part of this app.
