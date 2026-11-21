---
inclusion: always
---
# Product: หมอดิน AI (Mor Din AI)

Source: `docs/submission.md`. The project is at idea stage. There is no prototype and no AI test result yet.

Items marked **(assumption)** are new and still need team approval. Earlier assumptions are now confirmed by the team and carry no marker.

## Overview
- **Vision:** a LINE chatbot that turns a hard-to-read soil test sheet, a pH reading or a few typed soil values into fertilizer or soil-improvement advice a farmer understands at once, with the total amount and price for the farmer's own field, and answers follow-up questions in chat.
- **Pillar:** Agriculture & Food.
- **Team:** 5 people (PM, AI Engineer, Backend Developer, UX/Frontend Designer, Domain Expert/QA).
- **MVP cost target:** under 2,000 THB, not confirmed. The API cost must be recalculated from the number of test images and the number of chat turns.

## Problem
- Thai sugarcane farmers (about 3 million, about 10 million rai, 44% of the area in the Northeast) receive Department of Land Development (DLD) soil sheets full of numbers (OM, P, K, Ca, Mg, pH) and fertilizer formulas such as "46-0-0, 20.98 kg/rai". Most cannot read them.
- Fertilizer is about 24% of variable cost (about 3,260 THB/rai). The submission cites 94% of farmers lacking basic fertilizer knowledge, nitrogen use efficiency under 50%, and negative P and K balances.
- Northeast soil averages pH 5.70, while cane needs 6.0-6.5.
- Cane price and cost figures in the submission are estimates. Treat them as unverified before quoting them to users.

## Target users
- Primary: small-scale sugarcane farmers in the Northeast, many aged 50+. They use LINE already. Buttons and photos come first. Typing is optional (manual entry, field size and chat).
- Secondary (Phase 3): cooperatives and farmer groups, through a web dashboard.

## What the bot does

### The 6 components
| # | Component | Purpose |
|---|---|---|
| 1 | Interactive chat | Farmer asks follow-up questions or asks for advice |
| 2 | Lab sheet upload | Send a photo of a DLD soil test sheet |
| 3 | pH meter photo | Send a photo of the soil pH meter display |
| 4 | Manual entry | Type soil values (OM, P, K, Ca, Mg) or pH only |
| 5 | Cane price panel | Central reference cane price and prices by region |
| 6 | Usage guide | Plain explanation of how to use the tool, step by step |

### Order of steps (all input types)
1. The farmer sends the input (lab sheet photo, pH meter photo or typed values).
2. Photo input: the farmer confirms or corrects what the AI read. Typed input is taken as given.
3. **The bot asks the field size (`area_rai` after conversion).** The farmer can answer in rai, ngan, square wa, square metres or hectares, or a mix. It always asks, after step 2 and before any total quantity or price is worked out.
4. The result is built: per-rai amount, total amount for the field, estimated total price in THB.
5. The reply is a summary table, a shop script, and a plain explanation.

### What happens when data arrives (3 cases)
| Case | Input | Where the recommendation comes from | Result |
|---|---|---|---|
| Lab sheet | Photo of DLD sheet. Vision AI reads the 7 soil values (OM, P, K, Ca, Mg, pH, soil texture) **and the fertilizer formula and rate the sheet recommends**. The farmer confirms or corrects both. | **The sheet's own recommendation is used as is. It is not recalculated.** | Soil summary from the values. Sheet formula and rate (kg/rai) times `area_rai` gives total kg and estimated total price in THB. |
| Manual values | Farmer types OM, P, K, Ca, Mg and/or pH. | **Basic sugarcane fertilizer formula**, calculated by code from the typed values. | Fertilizer name, kg/rai, total kg for `area_rai` and estimated total price in THB for each fertilizer. |
| pH only | pH from a meter photo or typed. | pH class and soil-improvement table (`soil_amendments.json`). | Says whether the soil is acidic, alkaline or balanced. Gives first-step soil improvement: material type, approximate kg/rai, and total kg for `area_rai`. Recommends a lab soil test for accuracy. |

### When a photo cannot be read
- If the AI cannot read the photo, or cannot read some values (soil values, the sheet's formula and rate, or the pH on the meter), the bot says so and asks the farmer to **take the photo again, clearer**. It names what could not be read.
- The retake message gives short tips: put the sheet or meter flat in daylight, hold the phone steady and straight above it, fill the frame, keep out shadows and glare, and make sure the numbers are sharp.
- The bot never guesses an unreadable value and never invents a rate.
- If the retake still fails, the bot offers manual entry (component 4). Manual entry uses the basic sugarcane formula.
- (assumption) The tips are the same for the lab sheet and the pH meter, with the subject named in the message.

### Reply format and AI persona
- **Summary table:** every fertilizer or soil-improvement recommendation is shown as a table with: fertilizer (or material) name, amount per rai (kg/rai), **total amount for the field (kg)**, **estimated total price (THB)**, and a short description. The shop script is attached to it.
- **Shop script:** attached to every fertilizer recommendation. Plain, short, at most 3 sentences. It says the **approximate total weight in kg** the farmer needs ("ต้องการปุ๋ย ... ประมาณ N กิโล", whole kg) and the field size. It does **not** give bag counts or bag sizes, because each shop stocks different sizes.
- **Per 1 rai:** the reply tells the farmer how much to use on 1 rai in small bags, for example "ถ้าปุ๋ยถุงละ 5 กก. ใช้หว่านประมาณ 4 ถุงต่อ 1 ไร่ (ประมาณ 20.98 กก.)". The amount can also be applied to part of the field.
- **Language:** reply in the language the user typed (Thai reply to Thai, English reply to English). Button taps and photos with no text use Thai.
- **Tone:** friendly and conversational. No hard technical terms. Explain so a villager understands. Short but complete.
- **Expected benefit:** explain what applying the advice should do for cane yield. Word it as an expectation, not a guarantee.

## Confirmed parameters
The submission calls these "proposed". The items below are the ones the team set, so build to them.

| Parameter | Value |
|---|---|
| Main channel | LINE Official Account with Rich Menu (6 buttons, one per component: chat, lab sheet photo, pH meter photo, manual entry, cane prices, usage guide). Restart is a chat command ("เริ่มใหม่" / "restart"). |
| Secondary channel | Web dashboard, Phase 3 only |
| Initial audience | Small sugarcane farmers, Northeast Thailand |
| Lab sheet recommendation | Use the formula and rate printed on the sheet. No recalculation. |
| Manual entry recommendation | Basic sugarcane fertilizer formula, deterministic code (DLD guidance) |
| Field size | Asked every time before totals. Accepts rai, ngan, square wa, square metres, hectares, alone or combined. Converted to rai (`area_rai`) and shown back to the farmer. |
| Inputs | DLD lab sheet photo, pH meter photo, manual typing (OM, P, K, Ca, Mg, pH) |
| Scale approach | AI answers, no volunteer "soil doctors" (decision D4) |
| Pricing (later) | Freemium: free 3 uses/month, then 29 / 99 / 499 THB tiers |
| Language | Thai and English, following the language the user types. Plain wording, large buttons. |
| Output | Summary table (per-rai amount, total amount, total estimated price) plus shop script (3 sentences or fewer, approximate kg, no bag count) |
| Price display | Reference price as of the data date, always in THB (บาท) |

## Scope
- **P0 (MVP):**
  - F1 lab sheet photo to 7 soil values and the sheet's recommended formula and rate.
  - F2 pH meter photo.
  - F3 fertilizer amount: the sheet's rate for lab sheets, the basic sugarcane formula for manual entry.
  - F4 plain-language explanation, including the expected effect on yield.
  - F5 fertilizer price, per rai and total for the field, in THB.
  - F6 shop script, 3 sentences or fewer, with the total quantity.
  - F7 cane price panel: central reference price and regional prices (moved up from P1).
  - F10 interactive chat.
  - F11 manual entry of soil values or pH.
  - F12 pH-only advice: acidic, alkaline or balanced, plus soil-improvement material, kg/rai and total kg.
  - F13 summary table output.
  - F14 Thai and English replies.
  - F15 usage guide.
  - F16 ask the field size and work out total amount and price. The farmer may answer in rai, ngan, square wa, square metres or hectares, alone or combined (e.g. "3 ไร่ 2 งาน"). The bot converts the answer to rai (`area_rai`). (assumption) New ID.
- **P1 (if time allows):** F8 elder-friendly UX. F9 fertilizer application timing advice (e.g. applying during leaf/stomata opening periods to maximize nutrient uptake efficiency).
- **P2 (Phase 2+):** history, voice input, other crops, multiple lab formats, fertilizer shop ordering, cooperative dashboard.
- F10-F15 are confirmed IDs.

## Success criteria (MVP)
- Response time under 30 seconds.
- Farmer satisfaction of at least 80%.
- 10-50 pilot users.

## Rules for the product
- The farmer must confirm values read from a photo, including the sheet's recommended formula and rate, before any amount or price is worked out.
- The bot must ask `area_rai` before it gives total quantity or total price. It must not assume a default field size. If the farmer changes `area_rai`, the totals are redone.
- Lab sheet recommendations are never recalculated or changed by the bot. Only the farmer can correct them, at the confirm step.
- Fertilizer and soil-improvement numbers, including totals, come from the calculation code, never from the chat model. This holds in chat too.
- Prices are reference prices as of the data date, in Thai baht (THB / บาท), and always labeled "estimated" (ราคาโดยประมาณ). Mock prices in the submission are demo numbers, not data.
- The shop script is never longer than 3 sentences. It always gives the approximate total kg and the field size, and never gives a bag count or bag size.
- The yield effect is an expectation ("should help"), never a promise or a number we cannot support.
- Do not cite "a survey of 50 farmers", in the product, replies, docs or pitch. Describe the evidence as information gathered by asking real farmers who farm as a main or a side occupation.
- The pH-only result must say it is a first step and recommend a lab soil test.
- Never claim the AI has been validated until the 5-sheet test has passed.
- The example sheet (Lab ID 6801180) was not used to test AI. Do not put real personal data in prototypes.
- The Go/No-Go verdict is "proceed to validation planning", not ready for live use. Pilot comes after validation and safety checks.

## Bootcamp must-have feature
The single must-have feature for 21 Nov is the end-to-end soil sheet photo to fertilizer advice loop (running locally without LINE integration): the user uploads a seed photo of a DLD soil test sheet, Vision AI extracts the 7 values (OM, P, K, Ca, Mg, pH, soil texture) and the formula and rate the sheet recommends, the system displays them in plain language for the farmer to confirm or correct, the system then asks the field size in rai (`area_rai`), and only after that works out the total amount and estimated total price from the sheet's rate times `area_rai` (no recalculation of the formula). The reply is a summary table (name, kg/rai, total kg, estimated total THB, short description), a plain village-level explanation with the expected yield effect, and a shop script of 3 sentences or fewer that gives the total quantity.

The local build also shows the other 5 components so the whole tool can be demonstrated: chat, pH meter photo, manual entry (basic sugarcane formula, and the pH-only soil-improvement path, both asking `area_rai`), the cane price panel and the usage guide. The loop above must work first. The other components may be minimal. Replies follow the user's language (Thai or English).
