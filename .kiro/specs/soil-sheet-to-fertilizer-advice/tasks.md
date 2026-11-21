# Implementation Plan (3-hour hackathon build)

Scope follows `design.md`: three Thai-only flows. A is lab sheet upload, B is manual entry with full values, C is manual entry with only pH. Removed from this build: pH meter photo, cane prices, usage guide, English, chat, store-failure handling and property tests (see "Out of this build" in `requirements.md`).

**Required tasks** (no `*`) are the main flow demo of the must-have feature: lab sheet photo (read by Bedrock), confirm values, field size, then the summary table, the shop script and the plain explanation. **Optional tasks** are marked with `*` after the checkbox. Do them after the required ones, in the order listed.

## Time estimates

Each estimate is minutes of AI build time plus your review time. It includes running the tests for that task. It does not include AWS sign-in problems, `uv add` network delays, or bugs found only at integration.

| Group | Required | Optional |
|---|---|---|
| 1 Setup | 9 | 0 |
| 2 Data, loader, fixtures | 14 | 0 |
| 3 `fertilizer/` | 17 | 21 |
| 4 Session and `reduce()` | 21 | 10 |
| 5 Vision | 18 | 0 |
| 6 Explain | 18 | 14 |
| 7 Service, API, page | 21 | 0 |
| 8 Tests and checks | 6 | 14 |
| 9 README and final check | 5 | 3 |
| **Total** | **129 min** | **62 min** |

Required work is now 129 minutes, which is 9 minutes over the 120-minute limit. You chose to include the real Bedrock reader (task 5.3). Everything including the optional tasks is about 191 minutes (a little over 3 hours).

What the required build does not do: the explanation and the shop script come from templates (task 6.4* adds the model-written text), and manual entry (flows B and C) is not available. The Vision_Stub stays for tests and offline demos. Numbers are computed by code in every case.

To get back under 120 minutes you would have to cut about 9 minutes of scope. One option is the correction step in task 4.3 (the farmer could then only confirm or cancel, and a wrong reading means a retake).

- [ ] 1. Project setup (9 min)
  - [ ] 1.1 Update `pyproject.toml` and the package layout (5 min)
    - Add `[build-system]`, `src/` package config for `mordin`, and `[project.scripts] mordin = "mordin.main:run"`.
    - Run `uv add fastapi uvicorn python-multipart` and `uv add --dev pytest httpx`. Pillow is added in task 5.3.
    - Create the packages from `design.md` (`flows`, `vision`, `fertilizer`, `explain`, `storage`, `web`) and `tests/unit`, `tests/fixtures`. Add a `conftest.py` that blocks network access and removes AWS credential variables.
    - _Requirements: 21.1, 23.1_
  - [ ] 1.2 Write `config.py` (4 min)
    - `MODEL_ID`, `REGION`, `guard()` and `make_bedrock_model(max_tokens)` with explicit `max_tokens`, `connect_timeout=5` and `read_timeout=20`. Read `MORDIN_VISION_STUB` from the environment (default off, so the app calls Bedrock; tests and offline demos set it to 1).
    - _Requirements: 2.2, 18.6_

- [ ] 2. Data files, loader and fixtures (14 min)
  - [ ] 2.1 Seed data files (6 min)
    - `data/fertilizer_prices.json` (include one grade with no price), `data/dld_rules/basic_formula.json` (status bands, targets, `required_fields`: `om`, `p`, `k`, `ca`, `mg`), `data/limits.json`. Each has a demo `label` and an ISO `date` where time-sensitive.
    - Use clearly fake demo numbers, `placeholder: true` and the demo label in the rule file. `soil_amendments.json` is written in task 3.5*.
    - _Requirements: 21.3, 21.8, 9.12_
  - [ ] 2.2 `data.py` (5 min)
    - Load and validate the files above. Raise `DataFileError(path, reason)` that names the file. Reject a non-monotone target table and a placeholder file with no label. The amendment table loads in task 3.5*.
    - _Requirements: 9.5, 9.6, 9.8, 21.2_
  - [ ] 2.3 Lab sheet fixtures under `tests/fixtures/` (3 min)
    - Low K, high P, acidic pH below 6.0, one with a grade that has no price, one unreadable, one not-DLD (copy the stub readings from `agent.py`; leave `agent.py` as it is).
    - No real name, address, phone, Lab ID or sheet image.
    - _Requirements: 21.4, 21.5_

- [ ] 3. `fertilizer/` calculators and their unit tests
  - [ ] 3.1 `rounding.py` and `area.py` (6 min)
    - Half-up rounding. `parse_area` for rai, ngan, square wa, square metres and hectares, alone or combined, with a bare number as rai.
    - Tests: "3 ไร่ 2 งาน" is 3.5, "1 เฮกตาร์" is 6.25, "5" is 5. Reject 0, negative, non-number, repeated and unknown units.
    - _Requirements: 7.2, 7.3, 7.5, 7.10_
  - [ ] 3.2 `plan.py`, `totals.py` and `sheet_plan.py` (7 min)
    - `Plan`, `PlanItem`, `compute_item`, `build_sheet_plan`. The sheet rate passes through unchanged. No Demo_Rules.
    - Tests: 104.9 kg gives `script_kg` 105 and 60.0 gives 60. 20.98 kg per rai gives 4 small bags, 12 gives 2.5, 1 gives 0. A grade with no price gives `None`. Doubling `area_rai` doubles the unrounded total.
    - _Requirements: 8.1 to 8.7, 8.9_
  - [ ] 3.3 `formula.py`: `soil_status` only (4 min)
    - One status (good, fair, low, needs_action) per value, including texture, from the rule bands.
    - Tests with the lab sheet fixtures.
    - _Requirements: 13.2_
  - [ ]* 3.4 `formula.py`: `calculate_basic` and the manual fixtures (8 min)
    - Urea, DAP and MOP with clamp and supplied N, P2O5, K2O. Add the manual fixtures (full values with and without pH, missing fields).
    - Tests: expected amounts, same input gives same output, every amount within `[0, max]`, `p` at or above `p_sufficient` gives DAP 0, a hand-picked pair with higher P gives DAP not higher.
    - _Requirements: 9.1 to 9.13_
  - [ ]* 3.5 `amendments.py`, `data/soil_amendments.json` and pH-only fixtures (9 min)
    - Write the placeholder amendment table with the demo label. `classify_ph`, `build_ph_plan`, and the loader in `data.py`.
    - Tests: acidic, balanced and alkaline fixtures. Balanced gives no material. A class with no material gives no item. Totals for `area_rai`. A missing or invalid table raises the data error.
    - _Requirements: 10.1 to 10.9, 21.4_
  - [ ]* 3.6 `routing.py` (4 min)
    - `choose_path`: sheet, basic formula, pH only, or `NeedMoreValues(missing)`. A full-values set without pH goes to the basic formula.
    - Tests: lab sheet, full values with and without pH, pH only, not enough values.
    - _Requirements: 5.5 to 5.7_

- [ ] 4. Session, store and `reduce()`
  - [ ] 4.1 `Session` and `InMemoryStore` (4 min)
    - `Session` with states, retry counters and `pending`. `SessionStore` protocol and `InMemoryStore` only. No image bytes in the session.
    - _Requirements: 1.3, 2.8, 4.10_
  - [ ] 4.2 Events, commands and reply specs (3 min)
    - Event, command and `Reply(key, params, buttons)` types. No Thai text in `flows/`.
    - _Requirements: 13.9_
  - [ ] 4.3 `reduce()` for flow A (14 min)
    - Upload accepted, read ok or failed, retake message for unreadable fields, not-DLD reply, confirm, correct (3 invalid in a row return to the buttons), rate warning, cancel, restart, field size question and parsing (3 misses add restart and cancel), `BuildAdvice`, `result_sent`, changed field size after a result. Block any total while `area_rai` is `None`.
    - Typed text with no pending step gets the fixed "choose a button" reply. The restart command is checked first. Flow A goes straight to the sheet plan (no `routing.py` needed).
    - _Requirements: 3.1 to 3.6, 4.1 to 4.11, 6.1 to 6.7, 7.1 to 7.9_
  - [ ]* 4.4 `reduce()` for flows B and C (10 min)
    - Manual form with all six fields, validation, echo of accepted values, "done" button, missing-fields message, pH-only button, routing through `routing.py`. Needs tasks 3.4*, 3.5* and 3.6*.
    - Also: read retry counting (max 2) and the manual-entry button after 2 failed reads in a row.
    - _Requirements: 5.1 to 5.7, 18.2, 18.3_

- [ ] 5. Vision layer
  - [ ] 5.1 `vision/schemas.py` (3 min)
    - `SheetItem`, `SheetReading`, and `validate_reading()` that marks out-of-range values and unknown textures as `"unreadable"`.
    - _Requirements: 2.3, 2.9_
  - [ ] 5.2 `vision/stub.py` (3 min)
    - Fixture reader chosen by upload file name stem, else the default.
    - _Requirements: 2.6, 21.7_
  - [ ] 5.3 `vision/image.py`, `vision/reader.py` and `prompts/read_lab_sheet_v1.md` (12 min)
    - Run `uv add pillow`. `prepare_image`: JPEG or PNG by magic bytes, EXIF orientation, re-encode with metadata removed, downscale to at most 2560 px and 3.5 MB. Tests with generated images.
    - `read_lab_sheet`: fresh Strands agent per call with an image block, `structured_output_model=SheetReading` and a 20-second deadline. The prompt asks only for printed values and the sheet's formula and rate, and has no arithmetic.
    - _Requirements: 1.3, 1.5, 1.6, 2.1, 2.2, 2.7, 2.8, 2.10_

- [ ] 6. Explain layer
  - [ ] 6.1 `explain/messages.py`, Thai only (6 min)
    - `TH` dict for every reply key, item descriptions, retake tips, accuracy notices, the field size question, the "choose a button" reply, the menu hint line, and `render(reply)`.
    - _Requirements: 3.2, 13.9, 22.2, 22.3_
  - [ ] 6.2 `explain/table.py` (5 min)
    - `SummaryTable` with 5 columns, the `area_rai` heading, the total row, the estimated label and THB, and a plain-text copy. A row with no price shows "ไม่มีราคา".
    - _Requirements: 8.5, 11.1 to 11.6, 21.9_
  - [ ] 6.3 `explain/templates.py`, `explain/script.py` (template part) and a template-only `explain/advice.py` (7 min)
    - Templates for the soil summary, expected effect, per-rai guide and notices. `template_script` (3 sentences or fewer for any number of items). `build_advice` that assembles the blocks from templates and code.
    - _Requirements: 12.1, 12.2, 12.5, 13.1 to 13.6, 13.10, 13.11, 22.1_
  - [ ]* 6.4 Figure guard, script check and the model call in `advice.py` (14 min)
    - `check_figures`, `ScriptDraft` (at most 3 sentences), `check_script`, wording check for "verified", "guaranteed" and yield numbers. One structured call returning `AdviceText` with `prompts/explain_v1.md`, one 10-second deadline, one retry only for a bad script, and template fallback per block.
    - _Requirements: 12.3, 12.4, 13.7, 13.8, 18.4_

- [ ] 7. Service, API and page
  - [ ] 7.1 `service.py` (7 min)
    - Event loop for `ReadImage` (the Bedrock reader, or the stub when `MORDIN_VISION_STUB=1`) and `BuildAdvice`, the `ImageHolder`, step timing, the 30-second warning, and error logs with no values. A store error is logged and shows the generic Thai error bubble.
    - _Requirements: 18.5, 20.1 to 20.5_
  - [ ] 7.2 `main.py` (4 min)
    - `POST /api/start`, `POST /api/chat` and `GET /`. Upload checks (empty, not JPEG or PNG by magic bytes, over 10 MB) before any session. `run()` on `127.0.0.1`.
    - _Requirements: 1.1, 1.4 to 1.6, 21.1, 21.6_
  - [ ] 7.3 `web/static/index.html` following the "Web page (UI spec)" in `design.md` (10 min)
    - Mobile-first LINE-style chat: white header, light blue-gray chat area, white bot bubbles, green user bubbles, medium text (17 px), CSS variables for every color and size, no external fonts.
    - Menu chip for the lab sheet upload (the manual entry chip is added with task 4.4*), photo input without `capture`, stacked 48 px buttons, waiting and error bubbles, one card per fertilizer with the estimated total, the shop script card with a copy button, the copy-table button, the stub-data badge and the startup notice that AI reading accuracy has not been validated.
    - Check it on a phone-width window (about 390 px) and on a desktop window.
    - _Requirements: 1.2, 11.6, 21.7, 22.3_
- [ ] 8. Tests and checks
  - [ ] 8.1 One end-to-end integration test (6 min)
    - `TestClient`, Vision_Stub, `InMemoryStore`, template Explainer. Lab sheet fixture upload, confirm, field size "5". Assert the table totals equal rate times 5, the script has at most 3 sentences with the right `script_kg`, and the demo-data label shows.
    - _Requirements: 23.5_
  - [ ]* 8.2 Manual smoke test of flows B and C (6 min)
    - On the page, type full values (with and without pH), then only a pH. Check the table, the script and the notices. Check that a missing field gets the missing-fields message.
    - _Requirements: 5.1 to 5.7, 9.1, 10.1_
  - [ ]* 8.3 One live Bedrock check (8 min)
    - After AWS sign-in, run `uv run check_bedrock.py`, then `uv run mordin` with the stub off and one synthetic sheet photo (no real personal data). Record the response time and what the model returned. This is not an accuracy claim. Needs task 5.3. Strongly recommended even though it is optional: it is the only check that the real model call works.
    - _Requirements: 2.1, 20.2_

- [ ] 9. README and final check
  - [ ]* 9.1 Write the README (3 min)
    - How to run (`uv sync`, `uv run mordin`, `uv run pytest`), the stub switch, the demo data warning, and the statement that AI reading accuracy has not been validated against the lab sheet test set. Do not cite a survey of 50 farmers.
    - _Requirements: 22.4, 22.5_
  - [ ] 9.2 Final check (5 min)
    - Run `uv run pytest`. Run the flow A demo end to end on the page and confirm it asks the field size before any total. Search the repo for "50 farmers" wording and for real personal data. Leave `agent.py` as it is.
    - _Requirements: 7.7, 21.5, 22.5_
