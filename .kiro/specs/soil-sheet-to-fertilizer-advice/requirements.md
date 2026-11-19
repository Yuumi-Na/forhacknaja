# Requirements Document

## Introduction

This spec covers the single must-have feature for the 21 Nov bootcamp: an end-to-end loop that runs locally, without LINE integration. The farmer uses a minimal local web page with a LINE-style chat UI (chat bubbles, an image upload button, and Thai buttons). The farmer uploads a photo of a Department of Land Development (DLD) soil test sheet in the chat. A Vision AI step extracts 7 soil values (OM, P, K, Ca, Mg, pH, soil texture). The values are shown in plain Thai in a chat bubble so the farmer can confirm or correct them. Only after confirmation does the system calculate a field-specific N-P2O5-K2O fertilizer formula. The system then replies with a plain village-level Thai explanation that includes an estimated price per rai and a script to tell the fertilizer shop.

The team has approved placeholder demo DLD (TFT) rules stored in `data/dld_rules/`. These rules are clearly labeled as demo rules, are not real DLD guidance, and stay in place until the Domain Expert supplies the real tables. The advice must therefore carry a Thai label that it uses demo rules and must not be used for real fertilizer purchase decisions.

The build window is about 3 hours. The feature therefore uses seed and mock data, a stubbed login, and stubbed external services (LINE, cane price, database or session store, and an optional stub for the vision call). Testing is limited to basic unit tests and one integration test.

Out of scope: LINE integration, cane price lookup (P1), history, payments, dashboard, pH meter photo flow (F2), multiple lab sheet formats, and application timing advice (F9).

Sources: `docs/submission.md` (Solution Summary, Screens and Flows, Scope P0, Success Criteria) and the steering files `product.md`, `tech.md`, `structure.md`, `aws.md`.

### Assumptions

- (assumption A1, confirmed) The local interface is a minimal local web page with a LINE-style chat UI: chat bubbles, an image upload button, a text input for typed values, and Thai buttons for confirm, correct, cancel and restart. It is served locally and has no LINE integration. The web framework (FastAPI or similar) is a design decision.
- (assumption A2, approved) The team approves placeholder demo DLD (TFT) rules stored in `data/dld_rules/`. They are labeled as demo rules, are not real DLD guidance, and are used until the Domain Expert supplies the real tables.
- (assumption A3) Claude `anthropic.claude-sonnet-5` on Bedrock can read DLD sheets. This is untested. The 90% accuracy target is a later validation goal, not a claim of this feature.
- (assumption A4) The soil sheet format is the single DLD format shown by Lab ID 6801180. Other formats are treated as non-DLD.
- (assumption A5) Valid value ranges are set in a configuration file by the Domain Expert. Initial placeholder ranges: pH 3.0 to 10.0, OM 0 to 20 percent, P 0 to 500 mg/kg, K 0 to 1000 mg/kg, Ca 0 to 10000 mg/kg, Mg 0 to 2000 mg/kg. These are placeholders, not agronomic facts.
- (assumption A6) The soil texture values are a fixed list of Thai texture names, defined in configuration.
- (assumption A7) The "stubbed login" is a fixed demo user identifier supplied by configuration. No credentials are checked.
- (assumption A8) The session store is an interface with an in-memory or local file implementation for the demo. Supabase is out of scope for this feature.
- (assumption A9) The 30-second limit is measured from the moment the image is accepted until the final advice is shown, and excludes the time the farmer spends on the confirm step.
- (assumption A10) Seed fertilizer prices in `data/fertilizer_prices.json` are demo numbers, not market data.

## Glossary

- **Advice_Loop**: The local web application that runs the whole flow from image intake to the final Thai advice.
- **Chat_Page**: The local web page with a LINE-style chat UI: chat bubbles, an image upload button, a text input, and Thai buttons. It is served by the Advice_Loop and has no LINE integration.
- **Demo_User**: The fixed stub user identity used by the Advice_Loop in place of real login (assumption A7).
- **Farmer**: The person using the Chat_Page.
- **DLD**: Department of Land Development of Thailand, the issuer of the soil test sheet.
- **DLD_Sheet**: A soil test result sheet issued by the DLD in the format assumed in A4.
- **Soil_Values**: The 7 values OM, P, K, Ca, Mg, pH and soil texture. Field names in code are `om`, `p`, `k`, `ca`, `mg`, `ph`, `soil_texture`.
- **Vision_Reader**: The component that turns an image into Soil_Values using the Vision_Model.
- **Vision_Model**: Claude `anthropic.claude-sonnet-5` on Amazon Bedrock in Region ap-southeast-1, called through Strands.
- **Vision_Stub**: A replacement for the Vision_Reader that returns Soil_Values from a seed fixture without calling Bedrock.
- **Input_Validator**: The component that checks Soil_Values for presence and valid range.
- **Confirmation_Step**: The step where the Chat_Page shows the Soil_Values in Thai in a chat bubble and the Farmer chooses confirm, correct, or cancel with Thai buttons.
- **Demo_Rules**: The placeholder DLD (TFT) rule files in `data/dld_rules/`, approved under assumption A2. They are labeled as demo rules and are not real DLD guidance.
- **Demo_Rules_Label**: The Thai text stating that the formula uses demo rules and must not be used for real fertilizer purchase decisions.
- **Fertilizer_Calculator**: The deterministic Python component that applies the Demo_Rules to confirmed Soil_Values. It makes no model calls.
- **Fertilizer_Formula**: The result of the Fertilizer_Calculator: kilograms per rai of urea (46-0-0), DAP (18-46-0) and MOP (0-0-60), and the resulting N, P2O5 and K2O amounts.
- **Explainer**: The component that turns a Fertilizer_Formula into plain Thai text.
- **Advice_Message**: The final Thai chat message: soil health summary, fertilizer per rai with estimated price, shop script, and disclaimers.
- **Price_Table**: The seed file `data/fertilizer_prices.json` with demo prices and an ISO date field.
- **Session_Store**: The interface that holds the state of one Advice_Loop run. State names: `image_received`, `values_read`, `confirmed`, `result_sent`, `cancelled`, `failed`.
- **Rai**: A Thai land area unit used for fertilizer rates.
- **Estimated_Label**: The Thai text ราคาโดยประมาณ.

## Requirements

### Requirement 1: Start a session and accept a soil sheet image

**User Story:** As a farmer, I want to upload a photo of my DLD soil sheet in the chat, so that I do not have to read or type the numbers myself.

#### Acceptance Criteria

1. WHEN the Farmer opens the Chat_Page, THE Advice_Loop SHALL identify the user as the Demo_User without requesting a password, and SHALL complete identification within 1 second.
2. WHEN the Farmer uploads an image file in JPEG or PNG format with a size greater than 0 bytes and at most 10 MB (10,485,760 bytes) with the upload button, THE Advice_Loop SHALL accept the image, create exactly one session in the Session_Store, and set the session state to `image_received` within 2 seconds.
3. WHEN the Advice_Loop accepts an image, THE Chat_Page SHALL show a Thai chat bubble stating that the sheet was received and values are being read, within 2 seconds of acceptance.
4. IF the uploaded file is empty (0 bytes), cannot be read, or its content is not a JPEG or PNG image, THEN THE Chat_Page SHALL show a Thai chat bubble asking the Farmer to send a photo of the sheet, THE Advice_Loop SHALL create no session, and THE Chat_Page SHALL keep the upload button available.
5. IF the uploaded image is larger than 10 MB (10,485,760 bytes), THEN THE Chat_Page SHALL show a Thai chat bubble asking the Farmer to send a smaller photo, THE Advice_Loop SHALL create no session, and THE Chat_Page SHALL keep the upload button available.
6. IF the Session_Store fails to create the session, THEN THE Chat_Page SHALL show a Thai chat bubble telling the Farmer that the image could not be saved and asking the Farmer to try again, and THE Advice_Loop SHALL NOT proceed to value reading.

### Requirement 2: Extract the 7 soil values with Vision AI

**User Story:** As a farmer, I want the system to read the values from my sheet, so that I get advice for my own field.

#### Acceptance Criteria

1. WHEN a session is in state `image_received`, THE Vision_Reader SHALL send the image to the Vision_Model and request the Soil_Values as structured JSON, with a timeout of 20 seconds per call.
2. THE Vision_Reader SHALL call the Vision_Model with model ID `anthropic.claude-sonnet-5` and Region `ap-southeast-1`, with both values read from a single configuration location.
3. WHEN the Vision_Model returns a response within the timeout, THE Vision_Reader SHALL parse the response into a Soil_Values object with fields `om`, `p`, `k`, `ca`, `mg`, `ph` and `soil_texture`.
4. FOR ALL valid Soil_Values objects, serializing the object to JSON, parsing the JSON, and serializing again SHALL produce an equal object (round-trip property).
5. WHEN the Soil_Values object contains all 7 fields and every field is either a value or an explicit "unreadable" marker, THE Advice_Loop SHALL set the session state to `values_read`.
6. WHERE the Vision_Stub is enabled by configuration, THE Vision_Reader SHALL return Soil_Values from a seed fixture and SHALL make no Bedrock call.
7. THE Vision_Reader SHALL keep prompt text in a versioned file under `prompts/` and SHALL contain no fertilizer arithmetic in that prompt.
8. WHEN the Vision_Reader finishes reading, THE Advice_Loop SHALL delete the image bytes it holds in memory and SHALL write no image to the Session_Store.
9. IF the Vision_Reader cannot read a field with confidence, or a parsed value falls outside the valid range configured for that field, THEN THE Vision_Reader SHALL mark that field as unreadable instead of guessing, and THE Advice_Loop SHALL pass the marker to the Confirmation_Step so the Farmer is asked to supply that value.
10. IF the Vision_Model call fails, times out, is refused because of a Region or model ID restriction, or returns a response that cannot be parsed into the 7 fields, THEN THE Advice_Loop SHALL apply the failure handling in Requirement 8, SHALL NOT retry with any other model ID or Region, and SHALL keep the session in state `image_received`.

### Requirement 3: Handle unreadable images, non-DLD sheets, and incomplete or out-of-range values

**User Story:** As a farmer, I want clear guidance when my photo cannot be used, so that I know what to do next instead of getting wrong advice.

#### Acceptance Criteria

1. IF the Vision_Model reports that the image is blurry, too dark, cropped, or unreadable, THEN THE Chat_Page SHALL show a Thai chat bubble within 2 seconds of receiving the report. The bubble SHALL include photo tips (hold the phone steady, use daylight, include the whole page) and SHALL offer the manual entry option from Requirement 4 as a Thai button. THE Advice_Loop SHALL discard any partially read Soil_Values from that image and SHALL NOT run the fertilizer calculation.
2. IF the Vision_Model reports that the image is not a DLD_Sheet, THEN THE Chat_Page SHALL show a Thai chat bubble within 2 seconds of receiving the report. The bubble SHALL state that only DLD soil sheets are supported and SHALL offer the manual entry option from Requirement 4 as a Thai button. THE Advice_Loop SHALL discard any Soil_Values read from that image and SHALL NOT run the fertilizer calculation.
3. IF one or more of the 7 Soil_Values (`om`, `p`, `k`, `ca`, `mg`, `ph`, `soil_texture`) are missing from the parsed result, THEN THE Input_Validator SHALL mark each missing field as missing. THE Chat_Page SHALL show each missing field to the Farmer as "อ่านไม่ได้" in the Confirmation_Step and SHALL let the Farmer type a value for it in the chat input.
4. IF a numeric Soil_Value is below the configured minimum or above the configured maximum for its field, THEN THE Input_Validator SHALL mark the field as out of range. THE Chat_Page SHALL show the field with a Thai warning in the Confirmation_Step. The warning SHALL name the field and state the valid range, and the Farmer SHALL be able to edit the value.
5. IF the `soil_texture` value is not in the configured texture list, THEN THE Input_Validator SHALL mark the field as invalid. THE Chat_Page SHALL show the field with a Thai warning in the Confirmation_Step and SHALL let the Farmer correct it.
6. IF the Vision_Model response cannot be parsed into a Soil_Values object, or the Vision_Model call does not return within 20 seconds, THEN THE Advice_Loop SHALL treat the result as unreadable and apply criterion 1.
7. WHILE any Soil_Value is marked missing, out of range, or invalid, THE Advice_Loop SHALL block the transition from the Confirmation_Step to calculation. THE Advice_Loop SHALL allow the transition only after every flagged field holds a value that passes the Input_Validator checks and the Farmer has confirmed the values.

### Requirement 4: Confirm or correct the values in plain Thai

**User Story:** As a farmer, I want to see what the system read and fix any mistake, so that wrong readings do not lead to wrong fertilizer advice.

#### Acceptance Criteria

1. WHEN the session state becomes `values_read`, THE Confirmation_Step SHALL show in one chat bubble each of the 7 Soil_Values (OM, P, K, Ca, Mg, pH, soil texture) with a Thai label and unit, SHALL mark any Soil_Value that is missing, out of range, or invalid with a Thai warning next to that value, and SHALL offer exactly three Thai buttons: confirm, correct, and cancel.
2. WHEN the Farmer presses the confirm button and all 7 Soil_Values are present and within their configured valid ranges, THE Advice_Loop SHALL set the session state to `confirmed`.
3. IF the Farmer presses the confirm button while any Soil_Value is marked missing, out of range, or invalid, THEN THE Confirmation_Step SHALL keep the session state at `values_read`, SHALL show a Thai chat bubble naming each marked value, and SHALL offer the confirm, correct, and cancel buttons again.
4. WHEN the Farmer presses the correct button, THE Confirmation_Step SHALL ask in a Thai chat bubble for the name of the value to correct and SHALL then ask for the new value of that one Soil_Value, one value at a time. THE Farmer SHALL type the new value in the chat input.
5. WHEN the Farmer types a replacement for a numeric Soil_Value that is a number within the configured valid range for that value, THE Input_Validator SHALL accept it and THE Advice_Loop SHALL store it in place of the previous value.
6. IF the Farmer types a replacement that is not a number or is outside the configured valid range, THEN THE Confirmation_Step SHALL show a Thai chat bubble stating the accepted minimum and maximum, SHALL ask for the value again, and SHALL leave the stored value unchanged. IF the Farmer types 3 invalid replacements in a row for the same value, THEN THE Confirmation_Step SHALL return to the confirm, correct, and cancel buttons with the stored value unchanged.
7. WHEN the Farmer finishes a correction, THE Confirmation_Step SHALL show all 7 Soil_Values again and SHALL offer the confirm, correct, and cancel buttons again.
8. WHEN the Farmer presses the cancel button, THE Advice_Loop SHALL apply the cancel behavior in Requirement 5.
9. WHERE the Vision_Reader could not read the image and the Farmer chose manual entry, THE Confirmation_Step SHALL ask for all 7 Soil_Values one at a time in chat bubbles, applying the same validation as criteria 5 and 6, and SHALL then show all 7 values with the confirm, correct, and cancel buttons.
10. THE Advice_Loop SHALL record in the session, for each of the 7 Soil_Values, whether its current value was read by the Vision_Model or entered by the Farmer, and SHALL update that record to "entered by the Farmer" when a correction is accepted.
11. THE Fertilizer_Calculator SHALL run only on Soil_Values from a session whose state is `confirmed`.

### Requirement 5: Cancel and restart at the confirm step

**User Story:** As a farmer, I want to stop and start over if the reading is wrong or I changed my mind, so that I am never forced into advice I did not approve.

#### Acceptance Criteria

1. WHEN the Farmer presses the cancel button at the Confirmation_Step, THE Advice_Loop SHALL set the session state to `cancelled`, SHALL run no calculation, and THE Chat_Page SHALL show a Thai chat bubble within 3 seconds confirming that nothing was calculated.
2. WHEN a session enters the `cancelled` state, THE Advice_Loop SHALL discard all 7 Soil_Values (OM, P, K, Ca, Mg, pH, soil texture) and the uploaded image of that session, and THE Chat_Page SHALL offer within 3 seconds to start again with a new image.
3. WHEN the Farmer presses the restart button at any step before the Advice_Message is shown, THE Advice_Loop SHALL end the current session, discard its Soil_Values and uploaded image, and return the Chat_Page to the start state within 3 seconds.
4. WHEN the Farmer restarts, THE Advice_Loop SHALL create a new session that contains none of the 7 Soil_Values, no uploaded image, and no confirmation status from the earlier session.
5. WHILE a session is `cancelled`, WHEN a request to calculate arrives for that session, THE Advice_Loop SHALL reject the request, SHALL run no calculation, and THE Chat_Page SHALL show a Thai chat bubble asking the Farmer to start again.
6. IF the Farmer presses the restart button after the Advice_Message has been shown, THEN THE Advice_Loop SHALL treat the action as starting a new session, THE Chat_Page SHALL keep the earlier Advice_Message unchanged in the chat, and THE Chat_Page SHALL return to the start state.
7. IF discarding the Soil_Values fails during cancel or restart, THEN THE Advice_Loop SHALL keep the session in a state that blocks calculation, THE Chat_Page SHALL show a Thai chat bubble asking the Farmer to start again, and THE Advice_Loop SHALL NOT let any value from the failed session reach the new session.

### Requirement 6: Calculate the fertilizer formula deterministically with demo rules

**User Story:** As a farmer, I want a fertilizer formula calculated by fixed rules, so that the same soil values always give the same amounts.

#### Acceptance Criteria

1. WHEN a session reaches state `confirmed`, THE Fertilizer_Calculator SHALL compute a Fertilizer_Formula from the confirmed Soil_Values using the Demo_Rules loaded from `data/dld_rules/`.
2. THE Fertilizer_Calculator SHALL produce the amounts of urea, DAP and MOP in kilograms per rai, rounded to the nearest 1 kg (0.5 kg rounds up), with no model call.
3. THE Fertilizer_Calculator SHALL produce the target N, P2O5 and K2O amounts in kilograms per rai that the three fertilizers supply, rounded to the nearest 0.1 kg.
4. FOR ALL valid confirmed Soil_Values, THE Fertilizer_Calculator SHALL return the same Fertilizer_Formula on every run with the same input (determinism property).
5. FOR ALL valid confirmed Soil_Values, THE Fertilizer_Calculator SHALL return amounts that are greater than or equal to 0 kg per rai and less than or equal to the maximum per-rai amount defined in the Demo_Rules for each fertilizer.
6. FOR ALL valid confirmed Soil_Values, raising P while holding all other values constant SHALL NOT increase the DAP amount (monotonic property under the Demo_Rules).
7. WHERE the P value meets or exceeds the Demo_Rules "sufficient" threshold, THE Fertilizer_Calculator SHALL return a DAP amount of 0 kg per rai.
8. IF the Demo_Rules files are missing, unreadable, or fail schema validation, THEN THE Chat_Page SHALL show a Thai chat bubble stating that advice cannot be calculated right now, THE Advice_Loop SHALL set the session state to `failed` and show no fertilizer amounts, and THE Advice_Loop SHALL retain the confirmed Soil_Values in the session.
9. THE Fertilizer_Calculator package SHALL import no network or AWS client code, so that its tests run without credentials.
10. IF any confirmed Soil_Value is missing or outside the valid range defined in the configuration, THEN THE Fertilizer_Calculator SHALL return an error identifying the invalid field and no Fertilizer_Formula, and THE Chat_Page SHALL ask the Farmer in Thai to correct that value without changing the session state from `confirmed`.
11. WHEN the Fertilizer_Calculator computes a Fertilizer_Formula for a valid input, THE Fertilizer_Calculator SHALL complete within 1 second.
12. THE Demo_Rules files in `data/dld_rules/` SHALL contain a field with the Demo_Rules_Label and a field stating that the rules are placeholder demo rules and not real DLD guidance, and the Fertilizer_Calculator SHALL treat a Demo_Rules file without both fields as failing schema validation under criterion 8.
13. THE Fertilizer_Calculator SHALL return the Demo_Rules_Label read from the Demo_Rules together with every Fertilizer_Formula.

### Requirement 7: Explain the result in plain village-level Thai

**User Story:** As a farmer, I want a simple Thai explanation with prices and a shop script, so that I can see what the advice means and what to say at the shop.

#### Acceptance Criteria

1. WHEN the Fertilizer_Calculator returns a Fertilizer_Formula, THE Explainer SHALL produce an Advice_Message in Thai within 10 seconds of receiving the Fertilizer_Formula.
2. THE Advice_Message SHALL contain a soil health summary with exactly one status for each of the 7 Soil_Values (OM, P, K, Ca, Mg, pH, soil texture), and each status SHALL be one of four Thai wording categories: good (ดี), fair (พอใช้), low (ต่ำ), or needs action (ต้องเพิ่ม). The thresholds that map each Soil_Value to a category SHALL come from the Demo_Rules data and not from the Vision_Model.
3. THE Advice_Message SHALL contain, for each fertilizer in the Fertilizer_Formula, the Thai name, the formula grade (for example 46-0-0), and the kilograms per rai, with the kilogram value identical to the value in the Fertilizer_Formula, including the number of decimal places.
4. THE Advice_Message SHALL contain an estimated price in baht for each fertilizer and a total in baht per rai, each calculated by code from the Price_Table, and each price line SHALL carry the Estimated_Label (ราคาโดยประมาณ). Each price SHALL equal kilograms per rai multiplied by the Price_Table price per kilogram, rounded to the nearest whole baht, and the total SHALL equal the sum of the rounded per-fertilizer prices.
5. THE Advice_Message SHALL contain a shop script of 1 to 3 sentences that lists each fertilizer in the Fertilizer_Formula by Thai name, formula grade, and kilograms per rai, with the same values as in criterion 3.
6. THE Advice_Message SHALL state the Price_Table date in day-month-year form and a sentence that prices may differ from shop prices.
7. WHERE the Explainer uses the Vision_Model to phrase the text, THE Explainer SHALL pass the computed numbers to the Vision_Model as input, and THE Advice_Loop SHALL verify, before display, that every kilogram and baht figure in the output matches the computed values exactly and that no figure appears that is absent from the computed values.
8. IF a kilogram or baht figure in the model-phrased text differs from the computed values, or the Vision_Model call fails or does not return within 10 seconds, THEN THE Advice_Loop SHALL discard the model-phrased text, build a template-based Thai Advice_Message from the computed values, and show that message to the Farmer. The Farmer SHALL NOT see the discarded text.
9. THE Advice_Message SHALL use plain village-level Thai wording, SHALL NOT use a chemical symbol (for example N, P2O5, K2O) unless the same message explains it in Thai wording, and SHALL place each fertilizer line on its own line.
10. THE Advice_Message SHALL contain a notice that the advice is a guide based on the values the Farmer confirmed.
11. THE Advice_Message SHALL contain the Demo_Rules_Label returned by the Fertilizer_Calculator, stating in Thai that the formula uses demo rules and must not be used for real fertilizer purchase decisions, placed before the fertilizer lines.
12. THE Advice_Loop SHALL keep all Thai farmer-facing text in `src/mordin/explain/`, in `src/mordin/line/`, or in a Thai text resource file, and SHALL NOT place Thai farmer-facing text inside calculation code.
13. WHEN the Chat_Page shows the Advice_Message, THE Advice_Loop SHALL set the session state to `result_sent`.

### Requirement 8: Handle model call failures

**User Story:** As a farmer, I want a clear message when the AI service is unavailable, so that I can try again or type the values myself.

#### Acceptance Criteria

1. IF the call to the Vision_Model fails with a service error, an access error, or no response within 20 seconds, THEN THE Chat_Page SHALL show a Thai chat bubble stating that reading the sheet failed and offering a retry button and a manual entry button, and THE Advice_Loop SHALL keep the uploaded image in the session.
2. WHEN the Farmer presses the retry button after a Vision_Model failure, THE Vision_Reader SHALL repeat the call, up to a maximum of 2 retries per session.
3. IF the 2-retry limit for the session is reached and the Vision_Model call fails again, THEN THE Chat_Page SHALL show a Thai chat bubble stating that reading the sheet failed and offering only the manual entry button, with no retry button.
4. IF the Explainer model call fails with a service error, an access error, or no response within 10 seconds, THEN THE Advice_Loop SHALL show the template-based Thai Advice_Message built from the computed values, SHALL label prices as estimated (ราคาโดยประมาณ), and SHALL complete the reply within 30 seconds of the Farmer's confirmation.
5. WHEN a model call fails, THE Advice_Loop SHALL write one error log entry containing the failure type, the session identifier, and the step name, and SHALL include no Soil_Values, no image content, and no Farmer personal data in that entry.
6. IF a model call is configured with a Region other than `ap-southeast-1` or with a model ID that starts with `global.` or `apac.`, THEN THE Advice_Loop SHALL refuse to start the call, SHALL log a configuration error, and THE Chat_Page SHALL show the same Thai chat bubble and manual entry button as in criterion 1.

### Requirement 9: Handle an unreachable session store

**User Story:** As a farmer, I want the system to tell me honestly when it cannot save my progress, so that I do not lose or mix up my values.

#### Acceptance Criteria

1. IF the Session_Store does not respond within 5 seconds or returns an error when a session is created, THEN THE Chat_Page SHALL show a Thai chat bubble stating that the service is not ready and asking the Farmer to try again later, THE Advice_Loop SHALL make 0 calls to the Vision_Model, and THE Advice_Loop SHALL create no session.
2. IF the Session_Store does not respond within 5 seconds or returns an error after a session was created and before the state `result_sent`, THEN THE Advice_Loop SHALL stop at the current step, and THE Chat_Page SHALL show a Thai chat bubble stating that progress could not be saved, with a restart button in the same bubble.
3. IF the Session_Store does not respond within 5 seconds or returns an error during the transition to `confirmed`, THEN THE Advice_Loop SHALL make 0 fertilizer calculations, SHALL keep the session in its state before the transition, and THE Chat_Page SHALL show the Thai chat bubble required by criterion 2.
4. IF the Session_Store does not respond within 5 seconds or returns an error when recording `result_sent`, THEN THE Chat_Page SHALL still show the Advice_Message already computed, THE Advice_Loop SHALL write 1 log entry describing the store error, and THE Chat_Page SHALL show no error message to the Farmer.
5. THE Session_Store SHALL be an interface with at least 2 implementations, an in-memory implementation and a test double that fails every operation, so that the unreachable cases in criteria 1 to 4 can be tested without a real database.
6. WHILE the Session_Store is unreachable, THE Advice_Loop SHALL keep no Soil_Values in any storage after the current run ends, and SHALL reuse no Soil_Values from an earlier session or another farmer in a later run.

### Requirement 10: Response time

**User Story:** As a farmer, I want the advice quickly, so that I do not give up waiting.

#### Acceptance Criteria

1. WHEN the Farmer presses the confirm button, THE Chat_Page SHALL show the Advice_Message within 5 seconds of the confirmation when the Explainer uses the template.
2. WHEN an image is accepted and the Farmer requests no correction, THE Chat_Page SHALL show the Advice_Message within 30 seconds of the image being accepted, measured under assumption A9. The 30 seconds SHALL exclude the time the Farmer spends on the Confirmation_Step.
3. WHEN the Advice_Loop accepts an image, THE Chat_Page SHALL show a Thai waiting chat bubble within 2 seconds of accepting the image and SHALL keep it visible until the Vision_Reader returns values or fails.
4. WHEN a run finishes, THE Advice_Loop SHALL log the elapsed time in milliseconds of each step (read, confirm, calculate, explain) and the total elapsed time from image acceptance to the Advice_Message.
5. IF the elapsed time from image acceptance to the Advice_Message exceeds 30 seconds, THEN THE Advice_Loop SHALL log a slow-response warning that includes the elapsed time in milliseconds of each step, and THE Chat_Page SHALL still show the Advice_Message.

### Requirement 11: Seed data, stubs, and no real personal data

**User Story:** As a developer, I want the feature to run locally with fixtures and stubs, so that the team can demo and test it within the 3-hour window without accounts or real farmer data.

#### Acceptance Criteria

1. WHEN a developer runs a single `uv run` command from the repository root with no LINE credentials set, THE Advice_Loop SHALL start a local web server that serves the Chat_Page, and the Chat_Page SHALL complete one full cycle (image upload, confirmation, calculation, Advice_Message) without requesting or requiring any LINE credential.
2. IF a required file under `data/` (Price_Table, valid ranges, texture list, or Demo_Rules) is missing, unreadable, or fails to parse, THEN THE Advice_Loop SHALL stop before any calculation, THE Chat_Page SHALL show an error indicating which file is the problem, and THE Advice_Loop SHALL NOT use default values embedded in prompt text.
3. THE Advice_Loop SHALL read Price_Table values, valid ranges, the texture list, and Demo_Rules values only from files under `data/`, and SHALL contain none of these values in prompt text.
4. THE repository SHALL include at least 3 seed fixtures of Soil_Values under `tests/fixtures/`: one low-K case, one high-P case, and one acidic-pH case (pH below 6.0). Each fixture SHALL contain all 7 values (OM, P, K, Ca, Mg, pH, soil texture) and SHALL pass the valid-range check.
5. THE repository SHALL contain no real farmer name, address, phone number, Lab ID, or real DLD sheet image in fixtures, prompts, or logs.
6. THE Advice_Loop SHALL make 0 calls to LINE and 0 calls to any cane price source, and THE Advice_Message SHALL NOT display cane price.
7. WHILE the Vision_Stub is enabled, THE Chat_Page SHALL show, on the Confirmation_Step and in the Advice_Message, a Thai label stating that the values come from demo data.
8. THE Price_Table SHALL contain an ISO 8601 date field (YYYY-MM-DD) and a label stating that the prices are demo values.
9. WHEN the Chat_Page shows any fertilizer price, THE Chat_Page SHALL label it as estimated (ราคาโดยประมาณ).

### Requirement 12: Honest claims about accuracy

**User Story:** As a project lead, I want the system never to claim that the AI is validated, so that farmers and judges are not misled before the 20-sheet test is done.

#### Acceptance Criteria

1. THE Advice_Message SHALL contain no Thai or English wording that states or implies the reading or the advice is verified, certified, validated, approved, or guaranteed accurate.
2. WHEN the Confirmation_Step is shown, THE Confirmation_Step SHALL include a Thai sentence stating that the values were read by AI and may be wrong, in the same chat bubble as the 7 extracted values (OM, P, K, Ca, Mg, pH, soil texture) and before the confirm, correct, and cancel buttons.
3. WHEN the Farmer opens the Chat_Page, THE Chat_Page SHALL show a startup chat bubble stating that the AI reading accuracy has not been validated against the 20-sheet test set.
4. THE Advice_Loop README SHALL state that the AI reading accuracy has not been validated against the 20-sheet test set.

### Requirement 13: Testability of the core loop

**User Story:** As a developer, I want the core logic covered by basic unit tests and one integration test that run without credentials, so that the team can trust it in the 3-hour build.

#### Acceptance Criteria

1. WHEN the unit test suite for the Input_Validator, the Fertilizer_Calculator, the Confirmation_Step state machine, and the template Explainer runs on a machine with no network connection and no AWS credentials configured, THE test suite SHALL complete with every test passing or failing on code behavior alone, and with 0 network calls and 0 AWS credential lookups attempted.
2. THE unit test suite SHALL verify the round-trip behavior in Requirement 2 criterion 4 and the determinism, range, monotonic, and sufficient-threshold behavior in Requirement 6 criteria 4 to 7 with the seed fixtures and hand-written example inputs.
3. THE test suite SHALL include 1 integration test that runs the full loop (image received, values read, values confirmed, advice sent) with the Vision_Stub, the in-memory Session_Store, and a scripted confirm action, and asserts that the final Advice_Message is produced and contains the Demo_Rules_Label.
4. IF a test fails, THEN THE test suite SHALL report the input values and the expected and actual results of that test so that the failure can be reproduced.

## Agent design

### Agent job

The agent reads a DLD_Sheet photo into the 7 Soil_Values (`om`, `p`, `k`, `ca`, `mg`, `ph`, `soil_texture`) and, after the system has computed the Fertilizer_Formula, phrases the computed numbers as plain village-level Thai.

This job covers the Vision_Reader (Requirement 2) and the Explainer phrasing (Requirement 7, criterion 7). Model: `anthropic.claude-sonnet-5` (the Vision_Model) in `ap-southeast-1`, called through Strands.

### System prompt

> You read soil test sheets and write Thai text, and you do nothing else. When you are given a photo, read only the values printed on the Department of Land Development soil sheet: OM, P, K, Ca, Mg, pH and soil texture. Return each value exactly as printed, and return "unreadable" for any field you cannot read with confidence instead of guessing. If the photo is not a Department of Land Development soil sheet, or it is blurry, too dark, cropped or otherwise unreadable, return a reason code (`not_dld_sheet`, `blurry`, `too_dark`, `cropped` or `unreadable`) and no values. You never do fertilizer arithmetic, and you never invent, round, convert or change any number. When you are asked to phrase advice, use only the numbers the system passes to you, copy each kilogram and baht figure exactly, and add no figure that was not passed in. Write in plain village-level Thai that a farmer aged 50 or older understands, put each fertilizer on its own line, and explain any chemical symbol in Thai words. Never say or imply that the reading or the advice is verified, certified, validated, approved or guaranteed. Label every price ราคาโดยประมาณ, and say that the advice is a guide based on the values the farmer confirmed.

### Agent tools

Both tools return STUB data for now. Neither calls a real service.

| Tool name | Input | Output | Stub behavior |
|---|---|---|---|
| `read_soil_sheet_values` | `image_ref: str` (reference to the uploaded image held in memory) | `values`: object with `om`, `p`, `k`, `ca`, `mg`, `ph` (number or `"unreadable"`) and `soil_texture` (string or `"unreadable"`); or `reason_code`: one of `not_dld_sheet`, `blurry`, `too_dark`, `cropped`, `unreadable` | STUB. Returns a seed fixture from `tests/fixtures/` (Vision_Stub), or a reason code for an unreadable or non-DLD image. Makes no Bedrock call and no image analysis. |
| `get_fertilizer_prices` | none | `date`: str (ISO 8601, YYYY-MM-DD); `label`: str (demo-values label); `prices_per_kg`: object with `urea`, `dap`, `mop` (number, baht per kg) | STUB. Returns the demo values from `data/fertilizer_prices.json` (Price_Table). Makes no market or shop price lookup. |

### Kept out of the agent

The following stay as fixed code or screens. The agent does not decide, run or override any of them.

- Input validation and valid ranges (Requirement 3, Requirement 4 criteria 5 and 6, assumptions A5 and A6).
- The confirmation screen and the confirm, correct, cancel and restart buttons (Requirement 4, Requirement 5).
- The session state machine and the Session_Store (Requirement 1, Requirement 5, Requirement 9).
- The Demo_Rules fertilizer calculation, performed by the Fertilizer_Calculator (Requirement 6).
- Price arithmetic and totals, computed by code from the Price_Table (Requirement 7 criterion 4).
- The figure-matching check and the template fallback (Requirement 7 criteria 7 and 8, Requirement 8 criterion 4).
- Retry limits and timeouts (Requirement 2 criterion 1, Requirement 8 criteria 1 to 3, Requirement 9, Requirement 10).
- The Region and model-ID guard (Requirement 2 criterion 2, Requirement 8 criterion 6).
- The Demo_Rules_Label and the accuracy disclaimers (Requirement 6 criteria 12 and 13, Requirement 7 criterion 11, Requirement 12).
- Login, using the Demo_User stub (Requirement 1 criterion 1, assumption A7).
