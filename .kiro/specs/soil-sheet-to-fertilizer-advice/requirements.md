# Requirements Document

## Introduction

This spec covers the Bootcamp feature for 21 Nov: a tool that runs locally, without LINE integration, with all 6 components of หมอดิน AI on one minimal local web page with a LINE-style chat UI (chat bubbles, upload buttons, a text input, and buttons):

1. Interactive chat (F10).
2. Lab sheet upload (F1).
3. pH meter photo (F2).
4. Manual entry of soil values or pH (F11).
5. Cane price panel: central reference price and prices by region (F7).
6. Usage guide (F15).

Every input follows the same order: the farmer sends the input, confirms what the AI read (photo input only), **tells the field size**, and then receives a summary table, a shop script of 3 sentences or fewer, and a plain explanation. The recommendation comes from one of three places:

- **Lab sheet:** the Vision AI reads the 7 soil values (OM, P, K, Ca, Mg, pH, soil texture) and the fertilizer formula and rate printed on the sheet. After the farmer confirms them, the system uses the sheet's rate as is (no recalculation) and multiplies it by the field size.
- **Manual entry:** the system calculates fertilizer with the basic sugarcane fertilizer formula (deterministic code), then multiplies by the field size.
- **pH only:** the system says whether the soil is acidic, alkaline or balanced, gives soil-improvement material and kg per rai, multiplies by the field size, and recommends a lab soil test.

Replies are in the language the user typed (Thai or English).

The team approved placeholder demo rules stored in `data/dld_rules/` for the basic formula, and a placeholder soil-improvement table in `data/soil_amendments.json`. They are labeled as demo, are not real DLD guidance, and stay until the Domain Expert supplies the real tables. Results from them carry a label that they use demo rules and must not be used for real purchase decisions. Lab sheet rates come from the sheet itself, so the rules label does not apply to them. Prices are always demo values in this build.

The build window is short. The lab sheet loop is built first (see Priorities). The other components may be minimal. The feature uses seed and mock data, a stubbed login, and stubbed external services (LINE, cane price sources, database or session store, and an optional stub for the vision call). Testing is limited to basic unit tests and one integration test.

Out of scope: LINE integration, fetching cane prices from the web (P1), history, payments, dashboard, multiple lab sheet formats, voice input, elder-friendly UX work (F8), and application timing advice (F9).

Sources: `docs/submission.md` and the steering files `product.md`, `tech.md`, `structure.md`, `aws.md`.

### Priorities

- **Build first (flow A, lab sheet):** Requirements 1, 2, 3, 4, 6, 7, 8, 11, 12, 13, 18, 20, 21, 22, 23, as trimmed in "Out of this build" below.
- **Then (flows B and C, manual entry):** Requirements 5, 9, 10.
- **Not built in the 3-hour window:** Requirements 14, 15, 16, 17, 19 and the parts listed below.

### Out of this build (3-hour hackathon window)

The build keeps three Thai-only flows: A (lab sheet upload), B (manual entry with full values) and C (manual entry with only pH). See `design.md`. The requirements below stay in this file as the full product scope, but they are **not part of this build**. Do not implement or test them now. Re-adding them later needs no change to the rest.

| Requirement | Status in this build | What is cut |
|---|---|---|
| 1, criterion 2 | Trimmed | The Component_Menu has 2 entries (lab sheet upload, manual entry), not 6. |
| 1, criterion 3 | Trimmed | Upload applies to the lab sheet only. |
| 2 (criteria 1, 3, 5) | Trimmed | No pH meter photo reading. Lab sheet reading only. |
| 3 (criterion 2) | Trimmed | Retake message names lab sheet parts only. |
| 4 (criterion 1) | Trimmed | Confirmation shows lab sheet values only. |
| 10 (pH-only) | Trimmed | pH comes from typing only, not from a meter photo. |
| 14 (language) | Removed | Thai only. No language detection. Message keys stay so English can be added. |
| 15 (interactive chat) | Removed | No Chat_Agent. Typed text that does not answer a pending step gets a fixed Thai reply that points to the two buttons. |
| 16 (cane price panel) | Removed | No `data/cane_prices.json`, no panel. |
| 17 (usage guide) | Removed | A one-line hint on the page replaces it. |
| 19 (session store unreachable) | Removed | In-memory store only. A store error is logged and shows one generic Thai error bubble with a restart button. No `FailingStore`. |
| 21 (criteria 2, 4, 8) | Trimmed | No cane price file. Fixtures cover flows A, B and C. The Price_Table keeps its date and demo label. |
| 23 (testing) | Trimmed | Only unit tests for `fertilizer/` calculations (including amendments) and one end-to-end integration test. No Hypothesis property tests, no state machine test suite, no script-check unit tests. The script check and figure guard are covered by the integration test. |
| Agent design | Trimmed | Reader and Explainer stay. The Chat_Agent, `read_ph_meter`, `get_cane_prices` and the chat `build_plan` tool are not built. |

Requirements 5 to 13, 18, 20, 22 and the rest of 1 to 4 apply as written, with Thai as the only language.

### Assumptions

- (assumption A1, confirmed) The local interface is a minimal local web page with a LINE-style chat UI: chat bubbles, upload buttons, a text input, and buttons. It shows a component menu with the 6 components. It is served locally and has no LINE integration. The web framework (FastAPI or similar) is a design decision.
- (assumption A2, approved) The team approves placeholder demo rules in `data/dld_rules/` (basic formula and soil health thresholds) and `data/soil_amendments.json` (pH classes, materials and kg/rai). They are labeled as demo, are not real DLD guidance, and are used until the Domain Expert supplies the real tables. Replacing the files with real tables needs no change to these requirements except removing the demo label.
- (assumption A3) Claude `anthropic.claude-sonnet-5` on Bedrock can read DLD sheets and pH meter displays. This is untested. This feature makes no claim about reading accuracy.
- (assumption A4) The soil sheet format is the single DLD format shown by Lab ID 6801180. Other formats are treated as non-DLD.
- (assumption A5) Valid value ranges are set in a configuration file by the Domain Expert. Initial placeholder ranges: pH 3.0 to 10.0, OM 0 to 20 percent, P 0 to 500 mg/kg, K 0 to 1000 mg/kg, Ca 0 to 10000 mg/kg, Mg 0 to 2000 mg/kg, and a plausible sheet rate greater than 0 and at most 200 kg per rai. These are placeholders, not agronomic facts.
- (assumption A6) The soil texture values are a fixed list of Thai texture names, defined in configuration.
- (assumption A7) The "stubbed login" is a fixed demo user identifier supplied by configuration. No credentials are checked.
- (assumption A8) The session store is an interface with an in-memory or local file implementation for the demo. Supabase is out of scope for this feature.
- (assumption A9) The 30-second limit is the sum of two spans: from image acceptance until the Confirmation_Step is shown, and from the field size being accepted until the advice is shown. It excludes the time the Farmer spends on the confirm step and on answering the field size question.
- (assumption A10) Seed fertilizer prices in `data/fertilizer_prices.json` and seed cane prices in `data/cane_prices.json` are demo numbers, not market data.
- (assumption A11, confirmed) The manual entry form shows all six fields (OM, P, K, Ca, Mg, pH). The basic formula needs `om`, `p`, `k`, `ca` and `mg`. `ph` is optional. The formula itself uses `om`, `p` and `k`. `ca` and `mg` are required so the soil health summary covers them. The list is set in the Demo_Rules (`required_fields`).
- (assumption A12) pH class limits come from `data/soil_amendments.json`. Initial placeholder: acidic below 6.0, balanced from 6.0 to 6.5 inclusive, alkaline above 6.5. Cane's 6.0 to 6.5 target is the starting point. The Domain Expert sets the real limits.
- (assumption A13) The Reply_Language is `th` when the latest typed text contains any Thai character and `en` otherwise. With no text (button tap, photo only), the last Reply_Language of the session is kept, and the default is `th`.
- (assumption A14) The chat answers questions about sugarcane soil and fertilizer, and about this tool. It does not claim knowledge outside what the tools return.
- (assumption A15) Area conversions use 1 rai = 4 ngan = 400 square wa = 1,600 square metres, and 1 hectare = 6.25 rai.
- (assumption A16) The small bag used for the per-rai guide is `small_bag_kg` = 5, set in configuration.

## Glossary

- **Advice_Loop**: The local web application that runs the whole flow from input to the final advice.
- **Chat_Page**: The local web page with a LINE-style chat UI. It is served by the Advice_Loop and has no LINE integration.
- **Component_Menu**: The control on the Chat_Page that offers the 6 components: chat, lab sheet upload, pH meter photo, manual entry, cane prices, usage guide.
- **Demo_User**: The fixed stub user identity used by the Advice_Loop in place of real login (A7).
- **Farmer**: The person using the Chat_Page.
- **DLD**: Department of Land Development of Thailand, the issuer of the soil test sheet.
- **DLD_Sheet**: A soil test result sheet issued by the DLD in the format assumed in A4.
- **Soil_Values**: The 7 values OM, P, K, Ca, Mg, pH and soil texture. Field names in code are `om`, `p`, `k`, `ca`, `mg`, `ph`, `soil_texture`. Manual entry may leave any of `om`, `p`, `k`, `ca`, `mg`, `ph` empty.
- **Sheet_Recommendation**: The fertilizer formula and rate printed on the DLD_Sheet: a list of items, each with `fertilizer` (name or grade such as `urea` or `15-15-15`) and `rate_kg_per_rai`.
- **Vision_Reader**: The component that turns an image into Soil_Values and Sheet_Recommendation (lab sheet) or into `ph` (pH meter), using the Vision_Model.
- **Vision_Model**: Claude `anthropic.claude-sonnet-5` on Amazon Bedrock in Region ap-southeast-1, called through Strands.
- **Vision_Stub**: A replacement for the Vision_Reader that returns values from a seed fixture without calling Bedrock.
- **Input_Validator**: The component that checks values for presence and valid range.
- **Confirmation_Step**: The step where the Chat_Page shows what the AI read (and, for a lab sheet, the Sheet_Recommendation) and the Farmer chooses confirm, correct, or cancel.
- **Retake_Message**: The chat bubble that names what could not be read, gives photo tips, and asks for a clearer photo.
- **Area_Step**: The step where the Advice_Loop asks the Farmer for the field size.
- **Area_Parser**: The deterministic component in `fertilizer/` that turns the Farmer's field size answer into `area_rai`.
- **area_rai**: The field size in rai, a positive number.
- **Demo_Rules**: The placeholder rule files in `data/dld_rules/`, approved under A2. They hold the basic formula and the soil health thresholds. They are labeled as demo rules.
- **Demo_Rules_Label**: The text (Thai and English) stating that the result uses demo rules and must not be used for real fertilizer purchase decisions.
- **Sheet_Plan_Builder**: The deterministic component that turns a confirmed Sheet_Recommendation into Plan_Items without changing any rate.
- **Fertilizer_Calculator**: The deterministic Python component that applies the Demo_Rules (basic sugarcane formula) to typed Soil_Values. It makes no model calls.
- **Amendment_Calculator**: The deterministic component that classifies pH and reads the soil-improvement material and kg per rai from the Amendment_Table.
- **Amendment_Table**: The file `data/soil_amendments.json`: pH class limits, materials and kg per rai, with a demo label.
- **Totals_Calculator**: The deterministic component that turns `rate_kg_per_rai` and `area_rai` into `total_kg` and `total_price_thb`, the total into the whole-kg figure for the Shop_Script (`script_kg`), and the per-rai rate into the Small_Bag_Guide.
- **Plan_Item**: One row of a plan: name, `rate_kg_per_rai`, `total_kg`, `total_price_thb` (or "no price available"), and a short description key.
- **Small_Bag_Guide**: How much to use on 1 rai, told as a number of small bags of `small_bag_kg` (5 kg in configuration, A16) used for broadcasting, for example "about 4 small bags of 5 kg per rai".
- **Summary_Table**: The table of Plan_Items shown to the Farmer.
- **Shop_Script**: The text the Farmer can say at the shop: at most 3 sentences, with the total quantity of each item.
- **Explainer**: The component that turns a plan into plain-language text and the Shop_Script.
- **Advice_Message**: The final chat message: Summary_Table, Shop_Script, soil summary, expected effect, notices.
- **Chat_Agent**: The Strands agent behind the interactive chat. It gets numbers only from tools.
- **Price_Table**: The seed file `data/fertilizer_prices.json` with demo prices per kg and an ISO date field.
- **Cane_Price_Data**: The seed file `data/cane_prices.json` with a central reference cane price, prices by region, and an ISO date field.
- **Usage_Guide**: The static step-by-step text on how to use the tool, in Thai and English.
- **Reply_Language**: `th` or `en`, chosen under A13.
- **Session_Store**: The interface that holds the state of one Advice_Loop run. State names: `image_received`, `values_read`, `retake_needed`, `confirmed`, `area_requested`, `area_set`, `result_sent`, `cancelled`, `failed`.
- **Rai**: A Thai land area unit used for fertilizer rates.
- **Estimated_Label**: The text ราคาโดยประมาณ (Thai) or "estimated price" (English).

## Requirements

### Requirement 1: Start a session, show the 6 components, accept an image

**User Story:** As a farmer, I want to open the tool and pick what I want to do, so that I can send a photo, type values, check prices or ask a question without reading numbers myself.

#### Acceptance Criteria

1. WHEN the Farmer opens the Chat_Page, THE Advice_Loop SHALL identify the user as the Demo_User without requesting a password, and SHALL complete identification within 1 second.
2. WHEN the Chat_Page opens, THE Chat_Page SHALL show the Component_Menu with exactly 6 entries (chat, lab sheet upload, pH meter photo, manual entry, cane prices, usage guide), labeled in the Reply_Language.
3. WHEN the Farmer uploads an image file in JPEG or PNG format with a size greater than 0 bytes and at most 10 MB (10,485,760 bytes) after choosing the lab sheet or the pH meter entry, THE Advice_Loop SHALL accept the image, create exactly one session in the Session_Store recording which of the two entries was chosen, and set the session state to `image_received` within 2 seconds.
4. WHEN the Advice_Loop accepts an image, THE Chat_Page SHALL show a chat bubble stating that the image was received and is being read, within 2 seconds of acceptance.
5. IF the uploaded file is empty (0 bytes), cannot be read, or its content is not a JPEG or PNG image, THEN THE Chat_Page SHALL show a chat bubble asking the Farmer to send a photo, THE Advice_Loop SHALL create no session, and THE Chat_Page SHALL keep the upload button available.
6. IF the uploaded image is larger than 10 MB (10,485,760 bytes), THEN THE Chat_Page SHALL show a chat bubble asking the Farmer to send a smaller photo, THE Advice_Loop SHALL create no session, and THE Chat_Page SHALL keep the upload button available.
7. IF the Session_Store fails to create the session, THEN THE Chat_Page SHALL show a chat bubble telling the Farmer that the image could not be saved and asking the Farmer to try again, and THE Advice_Loop SHALL NOT proceed to value reading.

### Requirement 2: Read the image with Vision AI

**User Story:** As a farmer, I want the system to read my sheet or my meter, so that I get advice for my own field.

#### Acceptance Criteria

1. WHEN a session is in state `image_received`, THE Vision_Reader SHALL send the image to the Vision_Model and request structured JSON, with a timeout of 20 seconds per call. For a lab sheet the JSON SHALL hold the Soil_Values and the Sheet_Recommendation. For a pH meter photo the JSON SHALL hold `ph`.
2. THE Vision_Reader SHALL call the Vision_Model with model ID `anthropic.claude-sonnet-5` and Region `ap-southeast-1`, with both values read from a single configuration location.
3. WHEN the Vision_Model returns a response within the timeout, THE Vision_Reader SHALL parse it into an object with the fields `om`, `p`, `k`, `ca`, `mg`, `ph`, `soil_texture` and `sheet_recommendations` (lab sheet) or `ph` (pH meter).
4. FOR ALL valid objects, serializing to JSON, parsing, and serializing again SHALL produce an equal object (round-trip property), including every Sheet_Recommendation item.
5. WHEN every required field is either a value or an explicit "unreadable" marker, THE Advice_Loop SHALL set the session state to `values_read` if no required field is unreadable, and to `retake_needed` otherwise. The required fields are all 7 Soil_Values and at least one Sheet_Recommendation item for a lab sheet, and `ph` for a pH meter photo.
6. WHERE the Vision_Stub is enabled by configuration, THE Vision_Reader SHALL return values from a seed fixture and SHALL make no Bedrock call.
7. THE Vision_Reader SHALL keep prompt text in a versioned file under `prompts/`. THE prompt SHALL ask only for what is printed, and SHALL contain no fertilizer arithmetic and no instruction to calculate, adjust, convert or round any rate.
8. WHEN the Vision_Reader finishes reading, THE Advice_Loop SHALL delete the image bytes it holds in memory and SHALL write no image to the Session_Store.
9. IF the Vision_Reader cannot read a field with confidence, or a parsed value falls outside the valid range configured for that field, or a `soil_texture` value is not in the configured texture list, THEN THE Vision_Reader SHALL mark that field as unreadable instead of guessing.
10. IF the Vision_Model call fails, times out, is refused because of a Region or model ID restriction, or returns a response that cannot be parsed, THEN THE Advice_Loop SHALL apply the failure handling in Requirement 18, SHALL NOT retry with any other model ID or Region, and SHALL keep the session in state `image_received`.

### Requirement 3: Ask for a clearer photo when the image cannot be read

**User Story:** As a farmer, I want clear guidance when my photo cannot be used, so that I know how to take a better one instead of getting wrong advice.

#### Acceptance Criteria

1. IF the Vision_Model reports that the image is blurry, too dark, cropped or unreadable, or the session enters `retake_needed` under Requirement 2 criterion 5, THEN THE Chat_Page SHALL show the Retake_Message within 2 seconds, in the Reply_Language.
2. THE Retake_Message SHALL name which parts could not be read (soil values, the sheet's fertilizer formula or rate, or the pH), and SHALL give these photo tips: put the sheet or meter flat in daylight, hold the phone steady and straight above it, fill the frame with the sheet or display, avoid shadow and glare, and make sure the numbers are sharp. THE Retake_Message SHALL include an upload button for a new photo.
3. THE Advice_Loop SHALL NOT guess an unreadable value, SHALL NOT invent a rate, and SHALL NOT run any calculation while the session is in `retake_needed`.
4. WHEN a retake is uploaded, THE Advice_Loop SHALL discard all values read from the earlier image of that session and read the new image under Requirement 2.
5. IF 2 reads in a row in the same session end in `retake_needed`, THEN THE Chat_Page SHALL show the Retake_Message again together with a button for manual entry (Requirement 5), and SHALL keep the upload button available.
6. IF the Vision_Model reports that the image is not a DLD_Sheet, THEN THE Chat_Page SHALL show a chat bubble within 2 seconds stating that only DLD soil sheets are supported, with an upload button and a manual entry button. THE Advice_Loop SHALL discard any values read from that image and SHALL NOT run any calculation.

### Requirement 4: Confirm or correct what the AI read

**User Story:** As a farmer, I want to see what the system read, including the fertilizer rate on my sheet, and fix any mistake, so that wrong readings do not lead to wrong advice or a wrong amount to buy.

#### Acceptance Criteria

1. WHEN the session state becomes `values_read`, THE Confirmation_Step SHALL show in one chat bubble every value that was read, each with a label and unit in the Reply_Language. For a lab sheet this is the 7 Soil_Values and every Sheet_Recommendation item (fertilizer and kg per rai). For a pH meter photo this is `ph`. THE bubble SHALL offer exactly three buttons: confirm, correct, and cancel.
2. THE Confirmation_Step SHALL include, in the same bubble and before the buttons, a sentence stating that the values were read by AI and may be wrong.
3. IF a Sheet_Recommendation rate is greater than 0 and outside the plausible rate range configured under A5, THEN THE Confirmation_Step SHALL mark that item with a warning asking the Farmer to check the rate against the sheet.
4. WHEN the Farmer presses the confirm button, THE Advice_Loop SHALL set the session state to `confirmed`.
5. WHEN the Farmer presses the correct button, THE Confirmation_Step SHALL ask for the name of the value to correct (a Soil_Value, or the rate or the fertilizer of one Sheet_Recommendation item) and SHALL then ask for the new value of that one item, one at a time. THE Farmer SHALL type the new value in the chat input.
6. WHEN the Farmer types a replacement that is a number within the configured valid range for that value, or a rate greater than 0 and at most the plausible rate maximum, or a fertilizer name or grade in the form NN-NN-NN or a known fertilizer name, THE Input_Validator SHALL accept it and THE Advice_Loop SHALL store it in place of the previous value.
7. IF the Farmer types a replacement that is not valid, THEN THE Confirmation_Step SHALL show a chat bubble stating the accepted range or form, SHALL ask again, and SHALL leave the stored value unchanged. IF the Farmer types 3 invalid replacements in a row for the same value, THEN THE Confirmation_Step SHALL return to the confirm, correct and cancel buttons with the stored value unchanged.
8. WHEN the Farmer finishes a correction, THE Confirmation_Step SHALL show all values again and offer the confirm, correct and cancel buttons again.
9. WHEN the Farmer presses the cancel button, THE Advice_Loop SHALL apply the cancel behavior in Requirement 6.
10. THE Advice_Loop SHALL record in the session, for each value, whether its current value was read by the Vision_Model or entered by the Farmer, and SHALL update that record when a correction is accepted.
11. THE Advice_Loop SHALL NOT work out any amount or price for a photo input until the session state is `confirmed` and the Area_Step has set `area_rai`.

### Requirement 5: Enter soil values by hand

**User Story:** As a farmer, I want to type my soil values or only the pH, so that I can get advice when I have no photo or the photo cannot be read.

#### Acceptance Criteria

1. WHEN the Farmer chooses manual entry, THE Chat_Page SHALL show a chat bubble in the Reply_Language listing the fields OM, P, K, Ca, Mg and pH with their units and an example, and SHALL tell the Farmer that any of them may be typed, in one message or in several.
2. WHEN the Farmer types values, THE Input_Validator SHALL accept each number within the configured valid range for its field, SHALL reject any other with a chat bubble stating the accepted range, and SHALL leave previously accepted values unchanged.
3. THE Chat_Page SHALL show the accepted values back to the Farmer after each accepted message and SHALL offer a "done" button once at least one value is accepted.
4. WHEN the Farmer presses "done", THE Advice_Loop SHALL set the session state to `confirmed` and apply the Area_Step. Typed values need no separate confirm step.
5. IF the accepted values hold only `ph`, THEN THE Advice_Loop SHALL route to the pH-only path (Requirement 10).
6. IF the accepted values hold all the fields the Demo_Rules require (A11), THEN THE Advice_Loop SHALL route to the basic formula path (Requirement 9).
7. IF the accepted values hold neither only `ph` nor all the required fields, THEN THE Chat_Page SHALL name the missing required fields, SHALL ask the Farmer to type them, and, WHERE `ph` is present, SHALL offer a button to continue with pH-only advice. THE Advice_Loop SHALL NOT run a calculation until the Farmer does one of the two.

### Requirement 6: Cancel and restart

**User Story:** As a farmer, I want to stop and start over if the reading is wrong or I changed my mind, so that I am never forced into advice I did not approve.

#### Acceptance Criteria

1. WHEN the Farmer presses the cancel button at the Confirmation_Step, THE Advice_Loop SHALL set the session state to `cancelled`, SHALL run no calculation, and THE Chat_Page SHALL show a chat bubble within 3 seconds confirming that nothing was calculated.
2. WHEN a session enters `cancelled`, THE Advice_Loop SHALL discard all values, the Sheet_Recommendation, `area_rai` and the uploaded image of that session, and THE Chat_Page SHALL offer within 3 seconds to start again.
3. WHEN the Farmer presses the restart button, or types the restart command ("เริ่มใหม่" or "restart"), at any step before the Advice_Message is shown, THE Advice_Loop SHALL end the current session, discard its values, Sheet_Recommendation, `area_rai` and uploaded image, and return the Chat_Page to the start state within 3 seconds.
4. WHEN the Farmer restarts, THE Advice_Loop SHALL create a new session that contains none of the earlier values, no uploaded image, no `area_rai` and no confirmation status.
5. WHILE a session is `cancelled`, WHEN a request to calculate arrives for that session, THE Advice_Loop SHALL reject it, SHALL run no calculation, and THE Chat_Page SHALL show a chat bubble asking the Farmer to start again.
6. IF the Farmer restarts after the Advice_Message has been shown, THEN THE Advice_Loop SHALL treat the action as starting a new session, THE Chat_Page SHALL keep the earlier Advice_Message unchanged in the chat, and THE Chat_Page SHALL return to the start state.
7. IF discarding the values fails during cancel or restart, THEN THE Advice_Loop SHALL keep the session in a state that blocks calculation, THE Chat_Page SHALL show a chat bubble asking the Farmer to start again, and THE Advice_Loop SHALL NOT let any value from the failed session reach the new session.

### Requirement 7: Ask the field size and choose the result path

**User Story:** As a farmer, I want to say how big my field is, in the units I use, so that I am told exactly how much to buy.

#### Acceptance Criteria

1. WHEN the session state becomes `confirmed`, THE Chat_Page SHALL ask the Farmer for the field size in a chat bubble in the Reply_Language with an example, and THE Advice_Loop SHALL set the session state to `area_requested`.
2. THE Area_Parser SHALL accept a field size given in rai (ไร่), ngan (งาน), square wa (ตารางวา, ตร.ว.), square metres (ตารางเมตร, ตร.ม., m2) or hectares (เฮกตาร์), alone or combined in one answer such as "3 ไร่ 2 งาน 50 ตารางวา", and SHALL treat a bare number as rai.
3. THE Area_Parser SHALL convert the answer to `area_rai` using A15 and SHALL keep 4 decimal places.
4. WHEN the Area_Parser accepts an answer, THE Chat_Page SHALL show the converted value back to the Farmer (for example "3 ไร่ 2 งาน = 3.5 ไร่"), and THE Advice_Loop SHALL set the session state to `area_set`.
5. IF the answer is empty, zero, negative, not a number, or has an unknown unit, THEN THE Chat_Page SHALL ask again with the example, and THE Advice_Loop SHALL stay in `area_requested`. IF 3 invalid answers come in a row, THEN THE Chat_Page SHALL also offer the restart and cancel buttons.
6. THE Advice_Loop SHALL accept any positive `area_rai`, with no upper limit and no extra confirmation, because the field size is asked every time and shown back under criterion 4.
7. THE Advice_Loop SHALL NOT assume a default `area_rai`, and SHALL NOT work out any total quantity or total price while the session is not `area_set`. A request to do so SHALL be rejected and THE Chat_Page SHALL ask for the field size.
8. WHEN `area_set` and the plan source is known, THE Advice_Loop SHALL choose the result path from the data alone: a confirmed lab sheet Sheet_Recommendation uses the sheet path (Requirement 8), manual values with all required fields use the basic formula path (Requirement 9), and a `ph`-only input from a meter photo or from typing uses the pH-only path (Requirement 10).
9. WHEN the Farmer gives a different field size after a result was shown, THE Advice_Loop SHALL recalculate all totals and prices with the new `area_rai`, SHALL show a new Summary_Table, SHALL make no new Vision_Model call, and THE Chat_Page SHALL keep the earlier Advice_Message unchanged in the chat.
10. THE Area_Parser SHALL be deterministic, SHALL import no network or AWS client code, and SHALL be pure code with no model call.

### Requirement 8: Use the lab sheet's own recommendation

**User Story:** As a farmer, I want my sheet's fertilizer advice used as printed and scaled to my field, so that I buy the amount my sheet already recommends.

#### Acceptance Criteria

1. WHEN a lab sheet session is `area_set`, THE Sheet_Plan_Builder SHALL build one Plan_Item for each confirmed Sheet_Recommendation item, with `rate_kg_per_rai` equal to the confirmed rate.
2. THE Sheet_Plan_Builder SHALL NOT recalculate, adjust, round or replace any confirmed rate, and SHALL NOT use the Demo_Rules.
3. THE Totals_Calculator SHALL compute `total_kg` as `rate_kg_per_rai` multiplied by `area_rai`, rounded to the nearest 0.1 kg (0.05 rounds up).
4. THE Totals_Calculator SHALL compute `total_price_thb` as the rounded `total_kg` multiplied by the Price_Table price per kg for that fertilizer, rounded to the nearest whole baht.
5. IF a Sheet_Recommendation fertilizer has no price in the Price_Table, THEN THE Plan_Item SHALL show "no price available" instead of a price, and THE total price line SHALL state that it covers only the items that have a price. THE Advice_Loop SHALL NOT invent a price.
6. FOR ALL confirmed Sheet_Recommendation items, the Plan_Item `rate_kg_per_rai` SHALL equal the confirmed rate (pass-through property), and doubling `area_rai` SHALL double the unrounded total (proportional property).
7. THE Sheet_Plan_Builder and Totals_Calculator SHALL import no network or AWS client code, so that their tests run without credentials.
8. THE Advice_Message for a lab sheet SHALL NOT carry the Demo_Rules_Label for the amounts, because the amounts come from the sheet. It SHALL still carry the price label required by Requirement 11 criterion 5.
9. THE Totals_Calculator SHALL also compute `script_kg`, the `total_kg` rounded to the nearest whole kg (0.5 rounds up), for the Shop_Script, and `rate_small_bags_per_rai`, the `rate_kg_per_rai` divided by `small_bag_kg` and rounded to the nearest half bag (0.25 rounds up), for the Small_Bag_Guide.

### Requirement 9: Calculate fertilizer with the basic sugarcane formula (manual entry)

**User Story:** As a farmer without a lab sheet, I want a fertilizer formula calculated by fixed rules from my typed values, so that the same values always give the same amounts.

#### Acceptance Criteria

1. WHEN a manual entry session on the basic formula path is `area_set`, THE Fertilizer_Calculator SHALL compute the amounts from the typed values using the Demo_Rules loaded from `data/dld_rules/`.
2. THE Fertilizer_Calculator SHALL produce the amounts of urea (46-0-0), DAP (18-46-0) and MOP (0-0-60) in kilograms per rai, rounded to the nearest 1 kg (0.5 kg rounds up), with no model call, and SHALL produce the N, P2O5 and K2O amounts in kilograms per rai that the three fertilizers supply, rounded to the nearest 0.1 kg.
3. THE Totals_Calculator SHALL then compute `total_kg`, `total_price_thb`, `script_kg` and `rate_small_bags_per_rai` for each fertilizer under Requirement 8 criteria 3 to 5 and 9.
4. FOR ALL valid typed values, THE Fertilizer_Calculator SHALL return the same amounts on every run with the same input (determinism property).
5. FOR ALL valid typed values, THE Fertilizer_Calculator SHALL return amounts that are greater than or equal to 0 kg per rai and less than or equal to the maximum per-rai amount defined in the Demo_Rules for each fertilizer.
6. FOR ALL valid typed values, raising P while holding all other values constant SHALL NOT increase the DAP amount (monotonic property under the Demo_Rules).
7. WHERE the P value meets or exceeds the Demo_Rules "sufficient" threshold, THE Fertilizer_Calculator SHALL return a DAP amount of 0 kg per rai.
8. IF the Demo_Rules files are missing, unreadable, or fail schema validation, THEN THE Chat_Page SHALL show a chat bubble stating that advice cannot be calculated right now, THE Advice_Loop SHALL set the session state to `failed` and show no amounts, and THE Advice_Loop SHALL retain the accepted values in the session.
9. THE Fertilizer_Calculator package SHALL import no network or AWS client code, so that its tests run without credentials.
10. IF any accepted value is outside the valid range defined in the configuration, THEN THE Fertilizer_Calculator SHALL return an error identifying the invalid field and no amounts, and THE Chat_Page SHALL ask the Farmer to correct that value without changing the session state.
11. THE Fertilizer_Calculator SHALL complete within 1 second for a valid input.
12. THE Demo_Rules files SHALL contain a field with the Demo_Rules_Label and a field stating that the rules are placeholder demo rules and not real DLD guidance, and a file without both fields SHALL fail schema validation under criterion 8.
13. THE Fertilizer_Calculator SHALL return the Demo_Rules_Label read from the Demo_Rules together with every result.

### Requirement 10: Soil-improvement advice when only pH is known

**User Story:** As a farmer who only has a pH reading, I want to know whether my soil is acidic, alkaline or balanced and what to add, so that I can start improving it and know a lab test is still needed.

#### Acceptance Criteria

1. WHEN a pH-only session is `area_set`, THE Amendment_Calculator SHALL classify `ph` as `acidic`, `balanced` or `alkaline` using the class limits in the Amendment_Table (A12), with no model call.
2. THE Amendment_Calculator SHALL read from the Amendment_Table the soil-improvement material and the kg per rai for that class, and THE Totals_Calculator SHALL compute `total_kg`, `total_price_thb`, `script_kg` and `rate_small_bags_per_rai` under Requirement 8 criteria 3 to 5 and 9, using the Price_Table price for the material when it exists.
3. WHERE the class is `balanced`, THE Advice_Message SHALL state that no soil-improvement material is needed now and SHALL still recommend a lab soil test.
4. WHERE the Amendment_Table has no material for the class, THE Advice_Message SHALL state that no material can be advised and SHALL recommend a lab soil test, and SHALL show no amount.
5. THE Advice_Message SHALL say in plain words whether the soil is acidic, alkaline or balanced, SHALL say that this is a first step only, and SHALL recommend a lab soil test for accuracy. THE pH-only result SHALL NOT include a fertilizer formula.
6. FOR ALL valid `ph` values, THE Amendment_Calculator SHALL return the same class and the same amounts on every run (determinism property), and SHALL return a material amount greater than or equal to 0 kg per rai and at most the maximum in the Amendment_Table.
7. IF the Amendment_Table is missing, unreadable, or fails schema validation, THEN THE Advice_Loop SHALL apply criterion 8 of Requirement 9 with the Amendment_Table in place of the Demo_Rules.
8. THE Amendment_Table SHALL contain the Demo_Rules_Label and a field stating that its values are placeholder demo values, and THE Advice_Message SHALL show the Demo_Rules_Label.
9. THE Amendment_Calculator SHALL import no network or AWS client code.

### Requirement 11: Show the summary table and attach the shop script

**User Story:** As a farmer, I want one clear table with how much to buy and what it costs for my field, so that I can take it to the shop.

#### Acceptance Criteria

1. THE Advice_Message SHALL contain a Summary_Table with one row per Plan_Item and these columns: fertilizer or material name, amount per rai (kg/rai), total amount for the field (kg), estimated total price (THB), and a short description.
2. THE Summary_Table SHALL show `area_rai` in its heading, and SHALL show a total price row that equals the sum of the rounded Plan_Item prices that have a price.
3. THE Advice_Loop SHALL build the Summary_Table in code from the plan. Every kilogram and baht figure in it SHALL equal the computed value, including the number of decimal places.
4. THE short description of each Plan_Item SHALL come from a fixed text per fertilizer or material in the Reply_Language, not from the Vision_Model or any model.
5. EVERY price in the Summary_Table SHALL be in baht (THB, บาท), SHALL carry the Estimated_Label, and THE Advice_Message SHALL state the Price_Table date in day-month-year form and that prices may differ from shop prices.
6. THE Chat_Page SHALL show the Summary_Table as a table and SHALL also give a plain-text version of the same rows.
7. THE Advice_Message SHALL attach the Shop_Script (Requirement 12) to the Summary_Table for every plan, whether its items are fertilizers or soil-improvement materials.

### Requirement 12: Write the shop script in 3 sentences or fewer

**User Story:** As a farmer, I want a short script to read out at the shop, so that I can order the right amount at once.

#### Acceptance Criteria

1. THE Advice_Message SHALL contain a Shop_Script of 1 to 3 sentences in the Reply_Language, in plain and short wording.
2. THE Shop_Script SHALL name each Plan_Item and say the approximate total weight in kg (`script_kg`) that the Farmer needs, in the form "I need about N kg of ..." (Thai: "ต้องการปุ๋ย ... ประมาณ N กิโล"), and SHALL give the Farmer's `area_rai`. THE Shop_Script SHALL NOT give a number of bags or a bag size, because each shop stocks different sizes.
3. WHERE the Explainer uses the Vision_Model to write the Shop_Script, THE Explainer SHALL request it as structured output holding a list of at most 3 sentences, and SHALL pass the computed Plan_Items to the model as input.
4. IF the list holds more than 3 sentences, or a Plan_Item's `script_kg` or the `area_rai` does not appear in it exactly, or a figure with a weight, bag or money unit appears that is not one of those, or a bag count or bag size is given, THEN THE Advice_Loop SHALL discard it, retry once, and on a second failure SHALL build a template Shop_Script of at most 3 sentences from the computed values.
5. THE template Shop_Script SHALL name every Plan_Item within 3 sentences, whatever the number of items.

### Requirement 13: Explain the result in plain words with the expected effect

**User Story:** As a farmer, I want a simple explanation that tells me what the advice should do for my cane, so that I understand why to follow it.

#### Acceptance Criteria

1. WHEN the plan is complete, THE Explainer SHALL produce the Advice_Message text in the Reply_Language within 10 seconds.
2. FOR a lab sheet or manual entry result, THE Advice_Message SHALL contain a soil summary with exactly one status for each Soil_Value that was read or typed, and each status SHALL be one of four wording categories: good, fair, low, or needs action. THE thresholds SHALL come from the Demo_Rules data and not from a model. FOR a pH-only result the summary SHALL be the pH class.
3. THE Advice_Message SHALL contain a short explanation of what applying the advice should do for sugarcane yield. THE explanation SHALL use expectation wording ("should help"), SHALL give no yield number, and SHALL NOT promise or guarantee a result.
4. THE Advice_Message SHALL use plain, friendly, conversational wording that a farmer aged 50 or older understands, SHALL avoid hard technical terms, and SHALL NOT use a chemical symbol (for example N, P2O5, K2O) unless the same message explains it in plain words.
5. THE Advice_Message SHALL contain a notice that the advice is a guide based on the values the Farmer confirmed or typed.
6. WHERE the plan came from the Demo_Rules or the Amendment_Table, THE Advice_Message SHALL contain the Demo_Rules_Label before the Summary_Table.
7. WHERE the Explainer uses the Vision_Model to phrase the text, THE Explainer SHALL pass the computed numbers to the model as input, and THE Advice_Loop SHALL verify, before display, that every kilogram, bag, baht and `area_rai` figure in the output matches the computed values exactly and that no figure appears that is absent from them.
8. IF a figure differs, or the Vision_Model call fails or does not return within 10 seconds, THEN THE Advice_Loop SHALL discard the model-phrased text, build a template Advice_Message from the computed values, and show that message. THE Farmer SHALL NOT see the discarded text.
9. THE Advice_Loop SHALL keep all farmer-facing text in `src/mordin/explain/`, `src/mordin/line/`, `src/mordin/web/` or a text resource file, and SHALL NOT place farmer-facing text inside calculation code.
10. WHEN the Chat_Page shows the Advice_Message, THE Advice_Loop SHALL set the session state to `result_sent`.
11. THE Advice_Message SHALL tell the Farmer in plain words how much of each fertilizer or material to use on 1 rai, as the Small_Bag_Guide followed by the kg figure: for example "ถ้าปุ๋ยถุงละ 5 กก. ใช้หว่านประมาณ 4 ถุงต่อ 1 ไร่ (ประมาณ 20.98 กก.)". THE Advice_Message SHALL build it from `rate_small_bags_per_rai` and `rate_kg_per_rai`, so that the Farmer can also apply it to a part of the field. WHERE `rate_small_bags_per_rai` is 0, THE Advice_Message SHALL say "less than half a bag" instead of "0 bags".

### Requirement 14: Reply in the language the user types

**User Story:** As a user, I want answers in the language I wrote in, so that I understand them.

#### Acceptance Criteria

1. THE Advice_Loop SHALL set the Reply_Language under A13 for every typed message.
2. THE Chat_Page SHALL show every bubble, button, label, Retake_Message, field size question, Summary_Table text, Shop_Script, Usage_Guide and notice in the Reply_Language. Each fixed text SHALL exist in both `th` and `en`.
3. THE Advice_Loop SHALL pass the Reply_Language to every prompt that produces farmer-facing text, and SHALL NOT keep a separate copy of the logic per language.
4. WHEN the Farmer types a message in the other language, THE Advice_Loop SHALL switch the Reply_Language for the following bubbles.
5. THE language detection SHALL be pure code with no model call.

### Requirement 15: Interactive chat

**User Story:** As a farmer, I want to ask questions and get advice in chat, so that I can find out more after I see my result.

#### Acceptance Criteria

1. WHEN the Farmer chooses chat or types a question that is not an answer to a pending step, THE Chat_Agent SHALL answer in the Reply_Language in the same plain and friendly style as Requirement 13 criterion 4.
2. THE Chat_Agent SHALL state a fertilizer, soil-improvement, total quantity, price or cane price number only when a tool returned it in the current run, and SHALL say it is not sure instead of guessing when it has no tool result.
3. WHEN the Farmer asks for a fertilizer amount or price in chat, THE Chat_Agent SHALL use the confirmed values and `area_rai` of the session. IF either is missing, THEN THE Chat_Agent SHALL ask for them (photo, typed values or field size) before giving a total, and SHALL NOT assume a field size.
4. THE Chat_Agent SHALL NOT run fertilizer or soil-improvement arithmetic itself. It SHALL reach the Fertilizer_Calculator, the Sheet_Plan_Builder, the Amendment_Calculator and the Totals_Calculator only through tools.
5. THE Chat_Agent SHALL give no yield number and SHALL NOT promise a result.
6. THE Chat_Agent SHALL use model ID `anthropic.claude-sonnet-5` and Region `ap-southeast-1`, read from the single configuration location, with a timeout of 20 seconds.
7. IF the Chat_Agent model call fails or times out, THEN THE Chat_Page SHALL show a chat bubble stating that the answer is not available now and suggesting the buttons, and THE Advice_Loop SHALL write the log entry required by Requirement 18 criterion 5.
8. IF the question is outside A14, THEN THE Chat_Agent SHALL say so briefly and point to what it can help with.

### Requirement 16: Cane price panel

**User Story:** As a farmer, I want to see the central reference cane price and the price in my region, so that I know the market level.

#### Acceptance Criteria

1. WHEN the Farmer chooses cane prices, THE Chat_Page SHALL show the central reference cane price and the price for each region listed in the Cane_Price_Data, in baht (THB), with the Cane_Price_Data date in day-month-year form.
2. THE Advice_Loop SHALL read the prices only from `data/cane_prices.json` and SHALL make 0 calls to any cane price source on the web.
3. THE panel SHALL label the prices as reference prices as of that date and SHALL state that they may differ from the price the Farmer is paid. WHILE the Cane_Price_Data holds demo values, THE panel SHALL also state that the prices are demo values.
4. IF `data/cane_prices.json` is missing, unreadable or fails to parse, THEN THE Chat_Page SHALL show a chat bubble stating that prices are not available now, and the other components SHALL keep working.
5. THE Chat_Agent SHALL get cane prices only through a tool that reads the same file.

### Requirement 17: Usage guide

**User Story:** As a new user, I want a clear guide to the steps, so that I know how to use the tool.

#### Acceptance Criteria

1. WHEN the Farmer chooses the usage guide, or asks how to use the tool in chat, THE Chat_Page SHALL show the Usage_Guide in the Reply_Language.
2. THE Usage_Guide SHALL explain, in plain steps: how to send a lab sheet photo, how to send a pH meter photo, how to type values, that the Farmer checks what the AI read, that the tool asks the field size (with the units accepted), what the summary table and the shop script are, how to ask questions in chat, how to see cane prices, and how to restart.
3. THE Usage_Guide SHALL include the photo tips from Requirement 3 criterion 2.
4. THE Usage_Guide SHALL be static text with no model call.

### Requirement 18: Handle model call failures

**User Story:** As a farmer, I want a clear message when the AI service is unavailable, so that I can try again or type the values myself.

#### Acceptance Criteria

1. IF the call to the Vision_Model fails with a service error, an access error, a response that cannot be parsed, or no response within 20 seconds, THEN THE Chat_Page SHALL show a chat bubble stating that reading the image failed and offering a retry button and a manual entry button, and THE Advice_Loop SHALL keep the uploaded image in the session.
2. WHEN the Farmer presses the retry button after a Vision_Model failure, THE Vision_Reader SHALL repeat the call, up to a maximum of 2 retries per session.
3. IF the 2-retry limit is reached and the call fails again, THEN THE Chat_Page SHALL show a chat bubble stating that reading the image failed and offering only the manual entry button, with no retry button.
4. IF the Explainer model call fails with a service error, an access error, or no response within 10 seconds, THEN THE Advice_Loop SHALL show the template Advice_Message and template Shop_Script built from the computed values, SHALL label prices as estimated, and SHALL complete the reply within 30 seconds under A9.
5. WHEN a model call fails, THE Advice_Loop SHALL write one error log entry containing the failure type, the session identifier, and the step name, and SHALL include no soil values, no image content, and no Farmer personal data in that entry.
6. IF a model call is configured with a Region other than `ap-southeast-1` or with a model ID that starts with `global.` or `apac.`, THEN THE Advice_Loop SHALL refuse to start the call, SHALL log a configuration error, and THE Chat_Page SHALL show the same bubble and manual entry button as in criterion 1.

### Requirement 19: Handle an unreachable session store

**User Story:** As a farmer, I want the system to tell me honestly when it cannot save my progress, so that I do not lose or mix up my values.

#### Acceptance Criteria

1. IF the Session_Store does not respond within 5 seconds or returns an error when a session is created, THEN THE Chat_Page SHALL show a chat bubble stating that the service is not ready and asking the Farmer to try again later, THE Advice_Loop SHALL make 0 calls to the Vision_Model, and THE Advice_Loop SHALL create no session.
2. IF the Session_Store does not respond within 5 seconds or returns an error after a session was created and before the state `result_sent`, THEN THE Advice_Loop SHALL stop at the current step, and THE Chat_Page SHALL show a chat bubble stating that progress could not be saved, with a restart button in the same bubble.
3. IF the Session_Store does not respond within 5 seconds or returns an error during the transition to `confirmed` or to `area_set`, THEN THE Advice_Loop SHALL make 0 calculations, SHALL keep the session in its state before the transition, and THE Chat_Page SHALL show the bubble required by criterion 2.
4. IF the Session_Store does not respond within 5 seconds or returns an error when recording `result_sent`, THEN THE Chat_Page SHALL still show the Advice_Message already computed, THE Advice_Loop SHALL write 1 log entry describing the store error, and THE Chat_Page SHALL show no error message to the Farmer.
5. THE Session_Store SHALL be an interface with at least 2 implementations, an in-memory implementation and a test double that fails every operation, so that criteria 1 to 4 can be tested without a real database.
6. WHILE the Session_Store is unreachable, THE Advice_Loop SHALL keep no values in any storage after the current run ends, and SHALL reuse no values or `area_rai` from an earlier session or another farmer in a later run.

### Requirement 20: Response time

**User Story:** As a farmer, I want the advice quickly, so that I do not give up waiting.

#### Acceptance Criteria

1. WHEN the Farmer gives a valid field size, THE Chat_Page SHALL show the Advice_Message within 5 seconds when the Explainer uses the template.
2. WHEN an image is accepted and the Farmer requests no correction, THE Chat_Page SHALL show the Advice_Message within 30 seconds counted under A9.
3. WHEN the Advice_Loop accepts an image, THE Chat_Page SHALL show a waiting chat bubble within 2 seconds and SHALL keep it visible until the Vision_Reader returns values or fails.
4. WHEN a run finishes, THE Advice_Loop SHALL log the elapsed time in milliseconds of each step (read, confirm, area, calculate, explain) and the total counted under A9.
5. IF the total counted under A9 exceeds 30 seconds, THEN THE Advice_Loop SHALL log a slow-response warning with the elapsed time of each step, and THE Chat_Page SHALL still show the Advice_Message.

### Requirement 21: Seed data, stubs, and no real personal data

**User Story:** As a developer, I want the feature to run locally with fixtures and stubs, so that the team can demo and test it without accounts or real farmer data.

#### Acceptance Criteria

1. WHEN a developer runs a single `uv run` command from the repository root with no LINE credentials set, THE Advice_Loop SHALL start a local web server that serves the Chat_Page, and the Chat_Page SHALL complete one full cycle (image upload, confirmation, field size, Advice_Message) without requiring any LINE credential.
2. IF a required file under `data/` (Price_Table, Cane_Price_Data, Amendment_Table, valid ranges, texture list, or Demo_Rules) is missing, unreadable, or fails to parse, THEN THE Advice_Loop SHALL stop any calculation that needs it, THE Chat_Page SHALL show an error indicating which file is the problem, and THE Advice_Loop SHALL NOT use default values embedded in prompt text. A missing Cane_Price_Data SHALL affect only Requirement 16.
3. THE Advice_Loop SHALL read prices, valid ranges, the texture list, pH class limits and the Demo_Rules values only from files under `data/` or configuration, and SHALL contain none of these values in prompt text.
4. THE repository SHALL include these seed fixtures under `tests/fixtures/`: at least 3 lab sheet fixtures with all 7 Soil_Values and a Sheet_Recommendation (one low-K case, one high-P case, one acidic-pH case with pH below 6.0), one lab sheet fixture with a fertilizer grade that has no price, one manual entry fixture with all required fields, and pH-only fixtures for acidic, balanced and alkaline. Each SHALL pass the valid-range check.
5. THE repository SHALL contain no real farmer name, address, phone number, Lab ID, or real DLD sheet image in fixtures, prompts, or logs.
6. THE Advice_Loop SHALL make 0 calls to LINE and 0 calls to any cane price source.
7. WHILE the Vision_Stub is enabled, THE Chat_Page SHALL show, on the Confirmation_Step and in the Advice_Message, a label stating that the values come from demo data.
8. THE Price_Table and Cane_Price_Data SHALL each contain an ISO 8601 date field (YYYY-MM-DD) and a label stating that the prices are demo values.
9. WHEN the Chat_Page shows any fertilizer or material price, THE Chat_Page SHALL show it in baht and label it with the Estimated_Label.

### Requirement 22: Honest claims about accuracy

**User Story:** As a project lead, I want the system never to claim that the AI is validated, so that farmers and judges are not misled before the lab sheet test is done.

#### Acceptance Criteria

1. THE Advice_Message and every chat answer SHALL contain no Thai or English wording that states or implies the reading or the advice is verified, certified, validated, approved, or guaranteed accurate, and none that promises a yield result.
2. WHEN the Confirmation_Step is shown, THE Confirmation_Step SHALL contain the sentence required by Requirement 4 criterion 2.
3. WHEN the Farmer opens the Chat_Page, THE Chat_Page SHALL show a startup chat bubble stating that the AI reading accuracy has not been validated against the lab sheet test set.
4. THE Advice_Loop README SHALL state that the AI reading accuracy has not been validated against the lab sheet test set.
5. THE Advice_Loop, its README, its messages and its fixtures SHALL NOT cite a survey of 50 farmers. WHERE they describe the source of the farmer insight, they SHALL say it comes from asking real farmers who farm as a main or a side occupation.

### Requirement 23: Testability

**User Story:** As a developer, I want the core logic covered by basic unit tests and one integration test that run without credentials, so that the team can trust it.

#### Acceptance Criteria

1. WHEN the unit tests for the Input_Validator, the Area_Parser, the Sheet_Plan_Builder, the Totals_Calculator, the Fertilizer_Calculator, the Amendment_Calculator, the language detection, the Summary_Table builder, the Shop_Script check, the session state machine, and the template Explainer run on a machine with no network connection and no AWS credentials configured, THE test suite SHALL complete with every test passing or failing on code behavior alone, with 0 network calls and 0 AWS credential lookups attempted.
2. THE unit tests SHALL verify the round-trip behavior in Requirement 2 criterion 4, the pass-through and proportional behavior in Requirement 8 criterion 6, the determinism, range, monotonic and sufficient-threshold behavior in Requirement 9 criteria 4 to 7, and the determinism and range behavior in Requirement 10 criterion 6, with the seed fixtures and hand-written examples.
3. THE unit tests SHALL verify that the Area_Parser converts "3 ไร่ 2 งาน" to 3.5, "1 เฮกตาร์" to 6.25 and a bare "5" to 5, rejects 0, negative and non-numeric answers, and that the session state machine never reaches `result_sent` without `area_set`.
4. THE unit tests SHALL verify that a Shop_Script list of 4 sentences is rejected, that a script missing a Plan_Item's `script_kg` or the `area_rai` is rejected, and that a script that gives a bag count or bag size is rejected. THE unit tests SHALL also verify `script_kg` (104.9 kg gives 105 and 60.0 kg gives 60) and the Small_Bag_Guide with `small_bag_kg` 5 (20.98 kg per rai gives 4 bags, 12 kg gives 2.5 bags, 1 kg gives 0 and "less than half a bag").
5. THE test suite SHALL include 1 integration test that runs the lab sheet loop (image received, values read, values confirmed, field size given, advice sent) with the Vision_Stub, the in-memory Session_Store, and scripted confirm and field size actions, and asserts that the Advice_Message holds a Summary_Table whose totals equal the sheet rate multiplied by the given `area_rai`, and a Shop_Script of at most 3 sentences.
6. IF a test fails, THEN THE test suite SHALL report the input values and the expected and actual results of that test so that the failure can be reproduced.

## Agent design

### Agent jobs

- **Reader:** reads a DLD_Sheet photo into the 7 Soil_Values and the Sheet_Recommendation, or a pH meter photo into `ph` (Requirement 2).
- **Explainer:** after the system has computed the plan, phrases the computed numbers as plain text and writes the Shop_Script (Requirements 12 and 13).
- **Chat_Agent:** answers questions in chat, using tools for every number (Requirement 15).

Model for all three: `anthropic.claude-sonnet-5` in `ap-southeast-1`, called through Strands.

### System prompt (Reader and Explainer)

> You read soil test sheets and pH meter displays and write short plain text, and you do nothing else. When you are given a photo of a Department of Land Development soil sheet, read only what is printed: OM, P, K, Ca, Mg, pH, soil texture, and the fertilizer formula and rate per rai that the sheet recommends. When you are given a photo of a pH meter, read only the pH on the display. Return each value exactly as printed, and return "unreadable" for any field you cannot read with confidence instead of guessing. If the photo is not a Department of Land Development soil sheet, or it is blurry, too dark, cropped or otherwise unreadable, return a reason code (`not_dld_sheet`, `blurry`, `too_dark`, `cropped` or `unreadable`) and no values. You never do fertilizer arithmetic, and you never invent, round, convert, adjust or recalculate any number, including the recommended rate. When you are asked to phrase advice or write the shop script, use only the numbers the system passes to you, copy each kilogram, baht and field size figure exactly, and add no figure that was not passed in. Write in the language the system names (Thai or English), in plain, friendly words that a farmer aged 50 or older understands, with no hard technical terms. Explain any chemical symbol in plain words. Say what the advice should do for cane yield as an expectation, never as a promise and never with a yield number. The shop script is at most 3 sentences, names each item with the approximate total weight in kg that the system passes to you, and never gives a number of bags or a bag size. Never say or imply that the reading or the advice is verified, certified, validated, approved or guaranteed. Label every price as an estimated price in baht, and say that the advice is a guide based on the values the farmer confirmed.

### System prompt (Chat_Agent)

> You help sugarcane farmers with questions about their soil and fertilizer, and about how to use this tool. Reply in the language the farmer wrote in, in plain, friendly words. You never calculate. Every fertilizer, soil-improvement, quantity, price or cane price number you say must come from a tool result in this conversation. If you have no tool result, say you are not sure and say what the farmer can do (send a photo, type values, or give the field size). Never assume a field size. Never give a yield number, and never promise a result. Never say or imply that anything is verified, certified, validated, approved or guaranteed. Label every price as an estimated price in baht.

### Agent tools

All tools return STUB data for now. None calls a real service except the deterministic project code they wrap.

| Tool name | Input | Output | Stub behavior |
|---|---|---|---|
| `read_soil_sheet_values` | `image_ref: str` | `values`: object with `om`, `p`, `k`, `ca`, `mg`, `ph` (number or `"unreadable"`) and `soil_texture` (string or `"unreadable"`); `sheet_recommendations`: list of `{fertilizer: str, rate_kg_per_rai: number}` or `"unreadable"`; or `reason_code`: one of `not_dld_sheet`, `blurry`, `too_dark`, `cropped`, `unreadable` | STUB. Returns a seed fixture from `tests/fixtures/` (Vision_Stub), or a reason code. Makes no Bedrock call. |
| `read_ph_meter` | `image_ref: str` | `ph`: number or `"unreadable"`; or `reason_code` as above | STUB. Returns a seed pH fixture, or a reason code. |
| `get_fertilizer_prices` | none | `date`: str (ISO 8601); `label`: str (demo-values label); `prices_per_kg`: object keyed by fertilizer or material (number, baht per kg) | STUB. Returns the demo values from `data/fertilizer_prices.json`. |
| `get_cane_prices` | none | `date`: str (ISO 8601); `label`: str; `central_price_thb`: number; `regional_prices_thb`: object keyed by region | STUB. Returns the demo values from `data/cane_prices.json`. |
| `build_plan` | none (uses the session's confirmed values and `area_rai`) | `plan_source`: `sheet`, `basic_formula` or `ph_only`; `items`: list of Plan_Items; or `error` naming what is missing (for example `area_rai`) | Wraps the Sheet_Plan_Builder, Fertilizer_Calculator, Amendment_Calculator and Totals_Calculator. Deterministic code, no model call. |

### Kept out of the agent

The following stay as fixed code or screens. The agent does not decide, run or override any of them.

- Input validation and valid ranges (Requirements 3, 4 and 5, assumptions A5 and A6).
- The confirmation screen, the confirm, correct, cancel and restart buttons (Requirements 4 and 6).
- Field size parsing, unit conversion and the rule that no total comes before `area_set` (Requirement 7).
- The result path choice and all amounts: the sheet pass-through, the basic formula, the pH class, the soil-improvement amounts, and the totals and prices (Requirements 7 to 10).
- Building the Summary_Table, and the descriptions in it (Requirement 11).
- The 3-sentence and figure checks, and the template fallbacks (Requirements 12 and 13, Requirement 18 criterion 4).
- Language detection (Requirement 14).
- The session state machine and the Session_Store (Requirements 1, 6 and 19).
- Retry limits, timeouts, and the Region and model-ID guard (Requirements 2, 18, 19 and 20).
- The Demo_Rules_Label and the accuracy disclaimers (Requirements 9, 10, 13 and 22).
- Login, using the Demo_User stub (Requirement 1 criterion 1, assumption A7).
