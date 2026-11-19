---
inclusion: always
---
# Tech

Source: `docs/submission.md`, `pyproject.toml`, `agent.py`, `check_bedrock.py`, and the AWS rules in `aws.md`.

## Current state
- Python 3.12+, managed with uv. `pyproject.toml` lists one dependency: `strands-agents`.
- `agent.py` is a starter "PostPal" Strands agent, to be replaced with the หมอดิน AI agent. `check_bedrock.py` tests Bedrock access.
- There are no FastAPI, LINE SDK, test or lint dependencies yet, and no `[tool.*]` or scripts sections.

## Architecture
```
Farmer (LINE app)
  -> LINE Official Account (Rich Menu, LIFF)
  -> Webhook (FastAPI)
       1. Vision step: image -> 7 soil values (JSON)
       2. Confirm step: farmer confirms or edits values (LINE card)
       3. Calculation step: DLD (TFT) fertilizer formula
       4. Explain step: plain-language Thai reply, price, shop script
       5. Cane price lookup (P1)
  -> Database for sessions and (later) history
```
- Flows: A (lab sheet photo), B (pH meter photo), C (manual typing fallback).
- The conversation is a state machine: image received, values read, confirmed or edited, result sent.

## Technical decisions
| Decision | Choice | Status |
|---|---|---|
| Channel | LINE OA + Rich Menu + LIFF | From submission (D2) |
| Backend | FastAPI (Python) | From submission; not yet in `pyproject.toml` |
| Vision and language model | Claude `anthropic.claude-sonnet-5` on Bedrock, ap-southeast-1, through Strands | Team AWS rules. The submission proposes OpenAI GPT-4o Vision / GPT-4o-mini, which conflicts. (assumption) The AWS rules win. Confirm with the team. |
| Fertilizer math | Deterministic Python code applying the DLD formula, not LLM arithmetic | (assumption) The submission says "encode in a prompt". Code is easier to test. Needs team agreement. |
| Explanation | LLM turns computed numbers into plain Thai | From submission |
| Database | Supabase free tier | From submission |
| Hosting | Railway or Render free tier | From submission. (assumption) AWS is the team's account, so hosting may move to AWS. Confirm. |
| Cane price | Scrape sugarzone.in.th, OCSB, TSRI | From submission, P1 |
| Infrastructure as code | CDK or CloudFormation | AWS rules |

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
| Run tests | `uv run --with pytest pytest` (assumption) |

- `pyproject.toml` defines no run scripts, test runner or linter. The pytest command is an assumption: `.gitignore` lists `.pytest_cache/`, but pytest is not a dependency. If the team adopts it, run `uv add --dev pytest` and use `uv run pytest`.
- Once FastAPI is added, a local server command would be `uv run uvicorn app.main:app --reload` (assumption, depends on the layout in `structure.md`).
- `uv run` needs AWS credentials for Bedrock calls. Sign in first (`aws login`).

## Risks
| Risk | Level | Mitigation |
|---|---|---|
| AI misreads the lab sheet | High until tested | Farmer confirmation step, supported format limited to DLD sheets, test on at least 20 real sheets against expert-read values |
| Sheets differ by area or date | Medium | MVP supports DLD sheets only. Collect samples from several areas first. |
| Fertilizer prices differ from real prices | Medium | Label as estimated. Keep prices in a config file, not in prompts. |
| Elderly users send blurry photos | Medium | Photo guide plus manual typing fallback |
| pH meter OCR accuracy unknown | Medium | Test several meter brands. Manual fallback. |
| Cost estimate unverified | Medium | Recalculate from real image count. The 0.20-0.35 THB/image figure assumes GPT-4o pricing and does not apply to Bedrock. (assumption) |
| Response time over 30 s | Medium | Measure early. Keep prompts short. Use one model call for reading where possible. |
| Model choice conflict (OpenAI vs Bedrock) | Medium | Decide Bedrock now. See decisions table. |
| Personal data in photos | Medium | (assumption) Do not store images longer than needed. No real personal data in prototypes. |

## Assumptions
- (assumption) Bedrock Claude can read DLD lab sheets as well as GPT-4o. Untested. The 90% accuracy goal applies to whichever model is used.
- (assumption) DLD sheets share one format nationwide. The submission marks this unconfirmed.
- (assumption) The DLD (TFT) formula rules are available to the team as tables or equations. The submission does not include them.
- (assumption) Farmers will pay 29 THB/month. Unconfirmed, and out of MVP scope.
- (assumption) No competitor offers the full flow. Unconfirmed.
- (assumption) The LINE Messaging API free plan is enough for the pilot (10-50 users).
