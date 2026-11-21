---
inclusion: always
---
# Structure

This layout is confirmed by the team. The repo currently holds only `agent.py`, `check_bedrock.py`, `pyproject.toml`, `uv.lock` and `docs/`. Nothing below exists yet unless noted. **(assumption)** marks items added in this revision that still need approval.

## Folder layout
```
my-team/
├── .kiro/
│   ├── settings/mcp.json
│   └── steering/            product.md, tech.md, structure.md, aws.md
├── docs/
│   └── submission.md        source document (exists)
├── src/
│   └── mordin/              application package
│       ├── main.py          FastAPI app, LINE webhook route, local web routes
│       ├── config.py        settings read from environment variables, model ID, Region and guard
│       ├── data.py          loads and validates every file under data/ (no network)
│       ├── service.py       runs the commands the flows return (Bedrock, store), timing and error logs
│       ├── line/            LINE client, Flex card and text renderers, Rich Menu (6 buttons)
│       ├── web/             local demo page (static HTML) with the 6 components, no LINE
│       ├── flows/           conversation state machine (lab sheet, pH meter, manual, chat):
│       │                    confirm step, area step (asks area_rai, blocks the result until set),
│       │                    result path routing
│       ├── vision/          image -> soil values, the formula and rate printed on the lab sheet,
│       │                    or pH (Bedrock call, output schema). Each field is read or unreadable,
│       │                    never guessed. image.py re-encodes photos to fit the Bedrock image
│       │                    limit (3.75 MB, 8000 px) and removes metadata. stub.py reads fixtures.
│       ├── fertilizer/      basic sugarcane formula (manual entry), pH class, soil-improvement
│       │                    (amendment) rates, price table lookup, and total quantity and total
│       │                    price from area_rai. Lab sheet rates pass through here unchanged
│       │                    (multiplied by area_rai only). Also parses the farmer's
│       │                    field size (rai, ngan, sq wa, m2, hectare, combined) into area_rai.
│       │                    Deterministic, no network.
│       ├── explain/         user-facing text in Thai and English:
│       │                    language detection, summary table builder (SummaryTable, with
│       │                    per-rai amount, total kg and total price), shop script (max 3 sentences,
│       │                    includes total quantity), explanation with expected yield effect,
│       │                    area question text, usage guide text,
│       │                    chat agent (Strands, tools call fertilizer/ and prices/)
│       ├── prices/          central and regional cane price reader (data file), fetchers (P1)
│       └── storage/         database access
├── prompts/                 prompt text files, versioned
├── data/
│   ├── fertilizer_prices.json   estimated prices in THB per kg, with a "date" field
│   ├── cane_prices.json         central reference and regional cane prices in THB, with a "date" field
│   ├── soil_amendments.json     pH classes, amendment materials and kg/rai rates (Domain Expert source)
│   ├── limits.json              valid ranges, texture list, plausible sheet rate maximum, small_bag_kg
│   └── dld_rules/               DLD tables behind the basic sugarcane formula
├── tests/
│   ├── unit/                calculation, totals (area_rai), amendment, table, script-length, language,
│   │                        schema, flow tests (including "no result before area_rai")
│   ├── fixtures/            sample values and synthetic sheets (no real personal data)
│   └── eval/                accuracy check against the 20+ sheet set (values and recommended rate)
├── infra/                   CDK or CloudFormation (AWS rules prefer IaC)
├── scripts/                 one-off tools, e.g. check_bedrock.py
├── agent.py                 starter agent, remove when the real agent exists
├── pyproject.toml
└── uv.lock
```
- Move `check_bedrock.py` to `scripts/` only when the team agrees. Until then the commands in `tech.md` still point at the root.
- `src/` layout needs `[build-system]` and package config in `pyproject.toml`. Add this when the first module is written.

## Naming rules
- **Python files, modules, packages, functions, variables:** `snake_case`. Classes: `PascalCase`. Constants: `UPPER_SNAKE_CASE`.
- **Soil values:** use the same field names everywhere: `om`, `p`, `k`, `ca`, `mg`, `ph`, `soil_texture`. Put the unit in the name when it is not obvious, e.g. `p_mg_kg`, `om_percent`. Manual entry may leave any field empty (`None`).
- **Field size:** `area_rai` (float, rai). The farmer's answer in other units is converted to rai at the input edge, so everything downstream uses `area_rai` only. Use this name in code, prompts, schemas and tests. Do not use `area`, `rai` or `size`.
- **Amounts and prices:** `rate_kg_per_rai` for the per-rai amount, `total_kg` for the amount for the field, `unit_price_thb_per_kg` for the price per kg, `total_price_thb` for the estimated total price, `script_kg` for the shop script, `rate_small_bags_per_rai` and `small_bag_kg` for the per-rai small-bag guide.
- **Lab sheet recommendation:** `sheet_recommendations`, a list of items with `fertilizer` and `rate_kg_per_rai`.
- **Fertilizer names in code:** `urea` (46-0-0), `dap` (18-46-0), `mop` (0-0-60). Other grades printed on a sheet use the grade string as the key, e.g. `15-15-15`. Show Thai or English names only in user-facing text.
- **Soil-improvement names in code:** `agri_lime`, `dolomite` (the final list comes from `soil_amendments.json`). pH classes: `acidic`, `balanced`, `alkaline`.
- **Language codes:** `th`, `en`.
- **Feature references:** use submission IDs (F1-F16) in comments and commit messages, e.g. `F3: add urea rate calculation`. F10-F15 are confirmed. F16 (area question and totals) is new. (assumption)
- **Tests:** files `test_<module>.py`, functions `test_<behavior>`.
- **Prompt files:** `<task>_v<n>.md`, e.g. `read_lab_sheet_v1.md`. Do not edit a released version. Add a new one.
- **Data files:** lowercase, `snake_case`, with an ISO date field for anything time-sensitive.
- **Branches:** `feature/<id>-<short-name>`, `fix/<short-name>`.
- **Steering files:** lowercase, one topic per file.

## Language rules
- Code, identifiers, comments, commit messages: English.
- User-facing text is Thai or English, matching the language the user typed. Thai is the default when there is no text (button tap, photo only).
- User-facing text is kept in one place (`src/mordin/explain/` and `src/mordin/line/`, plus `src/mordin/web/` for the local page), not scattered through logic. Each message exists in both `th` and `en`. This includes the question that asks for the field size and the "please retake the photo" message with its tips.
- Prompts that produce user-facing text take the language code as an input. Do not keep separate copies of the logic per language.
- Thai text in prompts and data files must be saved as UTF-8.

## Placement rules
- No fertilizer or soil-improvement arithmetic in prompts, in `explain/`, in `line/` or in `web/`. It lives in `fertilizer/` only: the basic formula, pH classification, amendment material and kg/rai, per-rai to total conversion with `area_rai`, and price totals.
- The prompt that reads a lab sheet only extracts what is printed (values, formula, rate). It does not calculate or adjust any rate.
- The flow in `flows/` collects `area_rai` and holds it in the session. It does not multiply. `fertilizer/` receives `area_rai` as an argument.
- The chat agent in `explain/` may only report numbers returned by `fertilizer/` and `prices/` functions, called as tools.
- The summary table and the shop script are built in `explain/` from results computed in `fertilizer/`. The script prompt receives the computed totals as input. `line/` and `web/` only render them.
- Network and AWS calls live in `vision/`, `explain/`, `prices/`, `line/` and `storage/`. The `fertilizer/` and `flows/` packages stay free of them so they test without credentials.
- Secrets and tokens come from environment variables. `.env` is already git-ignored. Never commit it.
- The Bedrock model ID and Region are set once in `config.py` (`anthropic.claude-sonnet-5`, `ap-southeast-1`).
