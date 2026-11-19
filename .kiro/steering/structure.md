---
inclusion: always
---
# Structure

This is a proposal. The repo currently holds only `agent.py`, `check_bedrock.py`, `pyproject.toml`, `uv.lock` and `docs/`. Nothing below exists yet unless noted. (assumption) The team agrees to this layout.

## Proposed folder layout
```
my-team/
├── .kiro/
│   ├── settings/mcp.json
│   └── steering/            product.md, tech.md, structure.md, aws.md
├── docs/
│   └── submission.md        source document (exists)
├── src/
│   └── mordin/              application package
│       ├── main.py          FastAPI app and LINE webhook route
│       ├── config.py        settings read from environment variables
│       ├── line/            LINE client, message and card builders, Rich Menu
│       ├── flows/           conversation state machine (lab sheet, pH meter, manual)
│       ├── vision/          image -> soil values (Bedrock call, output schema)
│       ├── fertilizer/      DLD formula, deterministic calculation, price table
│       ├── explain/         plain-Thai explanation and shop script
│       ├── prices/          cane price fetchers (P1)
│       └── storage/         database access
├── prompts/                 prompt text files, versioned
├── data/
│   ├── fertilizer_prices.json   estimated prices, with a "date" field
│   └── dld_rules/               DLD formula tables
├── tests/
│   ├── unit/                calculation, schema, flow tests
│   ├── fixtures/            sample values and synthetic sheets (no real personal data)
│   └── eval/                accuracy check against the 20+ sheet set
├── infra/                   CDK or CloudFormation (AWS rules prefer IaC)
├── scripts/                 one-off tools, e.g. check_bedrock.py
├── agent.py                 starter agent, remove when the real agent exists
├── pyproject.toml
└── uv.lock
```
- Move `check_bedrock.py` to `scripts/` only when the team agrees. Until then the commands in `tech.md` still point at the root.
- `src/` layout needs `[build-system]` and package config in `pyproject.toml`. (assumption) Add this when the first module is written.

## Naming rules
- **Python files, modules, packages, functions, variables:** `snake_case`. Classes: `PascalCase`. Constants: `UPPER_SNAKE_CASE`.
- **Soil values:** use the same field names everywhere: `om`, `p`, `k`, `ca`, `mg`, `ph`, `soil_texture`. Put the unit in the name when it is not obvious, e.g. `p_mg_kg`, `om_percent`.
- **Fertilizer names in code:** `urea` (46-0-0), `dap` (18-46-0), `mop` (0-0-60). Show Thai names only in user-facing text.
- **Feature references:** use submission IDs (F1-F8) in comments and commit messages, e.g. `F3: add urea rate calculation`.
- **Tests:** files `test_<module>.py`, functions `test_<behavior>`.
- **Prompt files:** `<task>_v<n>.md`, e.g. `read_lab_sheet_v1.md`. Do not edit a released version. Add a new one.
- **Data files:** lowercase, `snake_case`, with an ISO date field for anything time-sensitive.
- **Branches:** `feature/<id>-<short-name>`, `fix/<short-name>`.
- **Steering files:** lowercase, one topic per file.

## Language rules
- Code, identifiers, comments, commit messages: English.
- Farmer-facing text: Thai, kept in one place (`src/mordin/explain/` and `src/mordin/line/`), not scattered through logic.
- Thai text in prompts and data files must be saved as UTF-8.

## Placement rules
- No fertilizer arithmetic in prompts or in the LINE layer. It lives in `fertilizer/`.
- Network and AWS calls live in `vision/`, `explain/`, `prices/`, `line/` and `storage/`. The `fertilizer/` and `flows/` packages stay free of them so they test without credentials.
- Secrets and tokens come from environment variables. `.env` is already git-ignored. Never commit it.
- The Bedrock model ID and Region are set once in `config.py` (`anthropic.claude-sonnet-5`, `ap-southeast-1`).
