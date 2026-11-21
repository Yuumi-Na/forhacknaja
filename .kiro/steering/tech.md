---
inclusion: always
---
# Tech

Source: `docs/submission.md`, `pyproject.toml`, `agent.py`, `check_bedrock.py`, and the AWS rules in `aws.md`.

Earlier assumptions are now confirmed by the team and carry no marker. **(assumption)** marks items added in this revision that still need approval. Confirmation of an assumption does not replace testing on real lab sheets.

## Current state
- Python 3.12+, managed with uv. `pyproject.toml` lists one dependency: `strands-agents`.
- `agent.py` is a starter "PostPal" Strands agent, to be replaced with the หมอดิน AI agent. `check_bedrock.py` tests Bedrock access.
- There are no FastAPI, LINE SDK, test or lint dependencies yet, and no `[tool.*]` or scripts sections.

## Architecture
```
Farmer (LINE app)                          Bootcamp demo (local browser, no LINE)
  -> LINE Official Account                   -> Local web page (same 6 components)
     (Rich Menu with 6 buttons, LIFF)
  -> Webhook / API (FastAPI)  <---------------- same backend
       Language: detect Thai or English from the user's text
       Component 1  Chat: Strands agent. Numbers only through tools that call fertilizer/ and prices/.
       Component 2  Lab sheet photo -> Vision step: image -> 7 soil values
                                       + the fertilizer formula and rate (kg/rai) printed on the sheet (JSON)
                                    -> Confirm step: farmer confirms or edits values and recommendation
       Component 3  pH meter photo  -> Vision step: image -> pH (JSON)
       Component 4  Manual entry    -> parse typed OM, P, K, Ca, Mg, pH (partial input allowed)
       Component 5  Cane price panel: central reference price + regional prices (dated data)
       Component 6  Usage guide: static text, Thai and English

       Area step (always, before calculation): ask area_rai, validate, store in session

       Calculation step (deterministic code, no LLM arithmetic):
         lab sheet    -> use the sheet's formula and rate as is (no recalculation)
                         total_kg = rate_kg_per_rai x area_rai, total price = total_kg x unit price
         manual values-> basic sugarcane fertilizer formula -> rate_kg_per_rai, then totals as above
         pH only      -> acidic / alkaline / balanced, soil-improvement material, kg/rai, total_kg
       Explain step: summary table (structured data) + shop script (max 3 sentences, with total quantity)
                     + plain explanation with expected yield effect, in the user's language
  -> Database for sessions and (later) history
```
- Flows: A (lab sheet photo), B (pH meter photo), C (manual typing), D (chat).
- Vision output marks each field as read or unreadable (value `null` plus a reason). If any needed field is unreadable, the flow goes to a "retake photo" state, not to the confirm step. The message names the unreadable part and gives photo tips. After a failed retake, manual entry is offered.
- Result path is chosen from the data and the source: lab sheet with a recommendation -> sheet rate. Manual values with enough soil values -> basic formula. pH only -> soil improvement.
- The conversation is a state machine: input received, values read, confirmed or edited, **area asked (`area_rai` set)**, result sent. The result state cannot be reached without `area_rai`. Chat can start from any state and uses the latest confirmed values and `area_rai`. If `area_rai` is missing, chat asks for it before giving totals.
- Output is built once as structured data (`SummaryTable`). The LINE layer renders it as a Flex Message with a plain-text fallback. The local web page renders it as an HTML table. LINE does not render Markdown tables.

## Technical decisions
| Decision | Choice | Status |
|---|---|---|
| Channel | LINE OA + Rich Menu (6 buttons) + LIFF | Confirmed (D2) |
| Local demo UI | FastAPI serving one static page with the 6 components, no LINE | Confirmed |
| Backend | FastAPI (Python) | Confirmed; not yet in `pyproject.toml` |
| Vision and language model | Claude `anthropic.claude-sonnet-5` on Bedrock, ap-southeast-1, through Strands | Confirmed. The AWS rules win over the submission's OpenAI GPT-4o proposal. |
| Lab sheet recommendation | Vision reads the soil values and the sheet's recommended formula and rate. After the farmer confirms, code multiplies the rate by `area_rai`. No new formula is calculated. | Confirmed |
| Manual entry fertilizer math | Deterministic Python code in `fertilizer/` applying the basic sugarcane fertilizer formula, not LLM arithmetic | Confirmed. (assumption) The Domain Expert signs off the exact equation before farmers see it. |
| Soil-improvement math (pH only) | Deterministic Python code: pH class (acidic / balanced / alkaline), material and kg/rai from a table in `data/`, then total kg for `area_rai` | Confirmed |
| Field size | The farmer may answer in rai, ngan, square wa (ตารางวา), square metres or hectares, alone or combined, e.g. "5", "5 ไร่", "3 ไร่ 2 งาน", "3 ไร่ 2 งาน 50 ตารางวา", "2 เฮกตาร์". A parser in `fertilizer/` converts to `area_rai` (float, rai) with 1 rai = 4 ngan = 400 square wa = 1,600 m2 and 1 hectare = 6.25 rai. A bare number means rai. Rejected if empty, zero, negative or not a number. The bot shows the converted value back ("3 ไร่ 2 งาน = 3.5 ไร่"). Any positive value is accepted, with no upper limit, because the size is asked every time and shown back. | (assumption) Units and conversions above are standard Thai land units. |
| Totals | `total_kg = rate_kg_per_rai x area_rai`. `total_price_thb = total_kg x unit price` from `data/fertilizer_prices.json`. Done in `fertilizer/` only. | (assumption) |
| Shop kg and small-bag guide | The shop script uses `script_kg` (total kg rounded to whole kg) and never a bag count or bag size. The per-rai guide uses `rate_small_bags_per_rai` = rate / `small_bag_kg` (5 kg, config), rounded to the nearest half bag. Done in `fertilizer/` only. | (assumption) |
| Interactive chat | Strands agent on Bedrock. Tools wrap `fertilizer/` and `prices/`. The agent states no fertilizer, soil-improvement, total or price number it did not get from a tool. | Confirmed |
| Explanation | LLM turns computed numbers into plain language, with the expected yield effect worded as an expectation | Confirmed |
| Summary table | Built in code from calculation results. Columns: name, kg/rai, total kg, estimated total price (THB), short description. Descriptions come from a fixed per-fertilizer text, not the model. | Confirmed |
| Shop script | LLM writes it as structured output: a list of at most 3 sentences. The computed `script_kg` per item and `area_rai` are passed in as input. Code rejects and retries a longer list, a script that lacks those figures, or one that gives a bag count, a bag size or any other figure with a unit. | Confirmed for the 3-sentence list. (assumption) The total check compares Arabic digits. |
| Language (TH/EN) | Detect from the user's text (Thai characters present -> Thai, else English). Photo or button input with no text keeps the last language, default Thai. The language is passed to the explain prompt. | Confirmed |
| Cane price panel | Central reference price and regional prices read from `data/cane_prices.json` with a `date` field. Scrapers (sugarzone.in.th, OCSB, TSRI) fill that file later. | Confirmed. Display is P0, scraping can stay P1. |
| Usage guide | Static Thai and English text, shown from the Rich Menu button and from chat | Confirmed |
| Database | Supabase free tier | Confirmed |
| Hosting | Railway or Render free tier | Confirmed that hosting may move to AWS, since AWS is the team's account. The platform is still to be chosen. |
| Infrastructure as code | CDK or CloudFormation | Confirmed (AWS rules) |

## AWS constraints (from `aws.md`)
- Region ap-southeast-1. The account refuses calls outside ap-southeast-1, ap-southeast-7 and us-east-1.
- Bedrock model ID is `anthropic.claude-sonnet-5`. Never use IDs starting with `global.` or `apac.`. This includes code the AgentCore CLI generates.
- AgentCore CLI is pinned at 0.30.0 (code agents, CodeZip). Do not install `@latest` or `@preview`, and do not use Harness commands unless asked.
- Never delete or change anything in the team account without asking.

## Commands
All commands run from the repo root.

| Purpose | Command |
|---|---|
| Install dependencies from `pyproject.toml` and `uv.lock` | `uv sync` |
| Check AWS sign-in and Bedrock access (prints `READY`) | `uv run check_bedrock.py` |
| Run the agent interactively (type `exit` to quit) | `uv run agent.py` |
| Add a dependency | `uv add <package>` |
| Run tests | `uv run --with pytest pytest` |

- `pyproject.toml` defines no run scripts, test runner or linter. pytest is not a dependency yet (`.gitignore` lists `.pytest_cache/`). When the team adopts it, run `uv add --dev pytest` and use `uv run pytest`.
- Once FastAPI is added, the local server command is `uv run uvicorn mordin.main:app --reload`. It depends on the layout in `structure.md` and on the package being installed.
- `uv run` needs AWS credentials for Bedrock calls. Sign in first (`aws login`).

## Risks
| Risk | Level | Mitigation |
|---|---|---|
| AI misreads the lab sheet values, or the recommended formula or rate | High until tested | Farmer confirmation step shows values and the recommendation. Supported format limited to DLD sheets. Test on at least 20 real sheets against expert-read values, including the rate. |
| A misread rate is multiplied by `area_rai`, so a money error grows with field size | High | The confirm step shows the rate before the area is asked. (assumption) `fertilizer/` flags a rate outside a plausible range set by the Domain Expert and asks the farmer to check it. |
| Photo, or part of it, cannot be read (values, recommended formula or rate, pH) | Medium | Say which part failed and ask for a clearer photo with tips (flat, daylight, steady, no glare, numbers sharp). Offer manual entry after a failed retake. Never guess a value or invent a rate. |
| Sheet lists a grade with no price | Medium | Show "no price available" for a grade not in the price file. Never invent a price. |
| Farmer gives a wrong `area_rai` or misunderstands the question | Medium | Short question with an example. Show `area_rai` back in the result table heading. Totals are redone if it changes. |
| Chat model invents fertilizer, amendment, total or price numbers | High | Chat gets numbers only through tools. Unit tests on the tools. Prompt tells the model to say "not sure" instead of guessing. |
| Basic sugarcane formula for manual entry is wrong | Medium | Domain Expert signs off the equation. Unit tests with expert-worked examples. |
| Soil-improvement rates (kg/rai) and pH class limits are entered wrongly | Medium | Domain Expert signs off `soil_amendments.json` before results are shown to farmers. |
| Yield claims overpromise | Medium | Expectation wording only. No yield numbers unless the Domain Expert supports them. |
| Shop script exceeds 3 sentences or shows a wrong total | Low | Structured output with a list limit, validated in code, with tests |
| Wrong reply language (mixed Thai and English input) | Low | Detect from the latest text message. Test mixed input. |
| Table unreadable on LINE | Medium | Flex Message card with a plain-text fallback. Five columns are tight on a phone, so test on a real phone. |
| Sheets differ by area or date | Medium | MVP supports DLD sheets only. Collect samples from several areas first. |
| Fertilizer and cane prices differ from real prices or go stale | Medium | Label as estimated, show the data date, THB only. Keep prices in data files, not in prompts. |
| Elderly users send blurry photos | Medium | Photo guide plus manual typing fallback |
| pH meter OCR accuracy unknown | Medium | Test several meter brands. Manual fallback. |
| Cost estimate unverified | Medium | Recalculate from real image count and chat turns. The 0.20-0.35 THB/image figure assumes GPT-4o pricing and does not apply to Bedrock. |
| Response time over 30 s | Medium | Measure early. Keep prompts short. Use one model call for reading where possible. The extra area question adds a turn, but no model call. |
| Personal data in photos | Medium | Do not store images longer than needed. No real personal data in prototypes. |

## Confirmed assumptions
These were assumptions in earlier versions. The team has confirmed them.
- Bedrock Claude can read DLD lab sheets as well as GPT-4o. This still has to be shown by test.
- DLD sheets share one format nationwide.
- The DLD (TFT) formula rules are available to the team as tables or equations. They back the basic sugarcane formula for manual entry.
- Soil-improvement material types (e.g. agricultural lime, dolomite) and kg/rai rates for acidic soil, and advice for alkaline soil, come from DLD or the Domain Expert. The pH ranges for acidic, balanced and alkaline are set by the Domain Expert. Cane's 6.0-6.5 target is the starting point.
- A central reference cane price and regional prices exist from a public source the team can read.
- Farmers will pay 29 THB/month.
- No competitor offers the full flow.
- The LINE Messaging API free plan is enough for the pilot (10-50 users).
- A Rich Menu with 6 areas fits the LINE layout limit.
- Images are not stored longer than needed.
