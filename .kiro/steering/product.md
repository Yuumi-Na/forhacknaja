---
inclusion: always
---
# Product: หมอดิน AI (Mor Din AI)

Source: `docs/submission.md`. The project is at idea stage. There is no prototype and no AI test result yet.

## Overview
- **Vision:** a LINE chatbot that turns a hard-to-read soil test sheet into fertilizer advice a farmer understands at once.
- **Pillar:** Agriculture & Food.
- **Team:** 5 people (PM, AI Engineer, Backend Developer, UX/Frontend Designer, Domain Expert/QA).
- **MVP cost target:** under 2,000 THB, not confirmed. The API cost must be recalculated from the number of test images.

## Problem
- Thai sugarcane farmers (about 3 million, about 10 million rai, 44% of the area in the Northeast) receive Department of Land Development (DLD) soil sheets full of numbers (OM, P, K, Ca, Mg, pH) and fertilizer formulas such as "46-0-0, 20.98 kg/rai". Most cannot read them.
- Fertilizer is about 24% of variable cost (about 3,260 THB/rai). The submission cites 94% of farmers lacking basic fertilizer knowledge, nitrogen use efficiency under 50%, and negative P and K balances.
- Northeast soil averages pH 5.70, while cane needs 6.0-6.5.
- Cane price and cost figures in the submission are estimates. Treat them as unverified before quoting them to users.

## Target users
- Primary: small-scale sugarcane farmers in the Northeast, many aged 50+. They use LINE already and should not need to type.
- Secondary (Phase 3): cooperatives and farmer groups, through a web dashboard.

## What the bot does
1. Receives a photo of a DLD soil sheet or a pH meter display.
2. Vision AI reads 7 values: OM, P, K, Ca, Mg, pH, soil texture.
3. The farmer confirms or corrects the values before any calculation.
4. The system calculates a field-specific fertilizer formula (N-P2O5-K2O) following DLD guidance.
5. The reply is in plain village-level Thai: soil health summary, fertilizer per rai with estimated price, a script to tell the fertilizer shop, and the daily cane price.

## Confirmed parameters
The submission calls these "proposed". The items below are the ones the team set, so build to them.

| Parameter | Value |
|---|---|
| Main channel | LINE Official Account with Rich Menu (3 buttons: lab sheet photo, pH meter photo, restart) |
| Secondary channel | Web dashboard, Phase 3 only |
| Initial audience | Small sugarcane farmers, Northeast Thailand |
| Fertilizer formula | DLD guidance (TFT) |
| Inputs | DLD lab sheet photo, pH meter photo, manual typing as fallback |
| Scale approach | AI answers, no volunteer "soil doctors" (decision D4) |
| Pricing (later) | Freemium: free 3 uses/month, then 29 / 99 / 499 THB tiers |
| Language | Thai, plain wording, large buttons |

## Scope
- **P0 (MVP):** F1 lab sheet photo to 7 values. F2 pH meter photo with manual fallback. F3 fertilizer calculation per DLD. F4 plain-language explanation. F5 fertilizer price per rai. F6 shop script.
- **P1 (if time allows):** F7 daily and regional cane price. F8 elder-friendly UX. F9 fertilizer application timing advice (e.g. applying during leaf/stomata opening periods to maximize nutrient uptake efficiency).
- **P2 (Phase 2+):** history, voice input, other crops, multiple lab formats, fertilizer shop ordering, cooperative dashboard.

## Success criteria (MVP)
- AI reading accuracy of at least 90% on at least 20 real lab sheets.
- Response time under 30 seconds.
- Farmer satisfaction of at least 80%.
- 10-50 pilot users.

## Rules for the product
- The farmer must confirm read values before the fertilizer calculation runs.
- Prices are always labeled "estimated" (ราคาโดยประมาณ). Mock prices in the submission are demo numbers, not data.
- Never claim the AI has been validated until the 5-sheet test has passed.
- The example sheet (Lab ID 6801180) was not used to test AI. Do not put real personal data in prototypes.
- The Go/No-Go verdict is "proceed to validation planning", not ready for live use. Pilot comes after validation and safety checks.

## Bootcamp must-have feature
The single must-have feature for 21 Nov is the end-to-end soil sheet photo to fertilizer advice loop (running locally without LINE integration): the user uploads a seed photo of a DLD soil test sheet, Vision AI extracts the 7 values (OM, P, K, Ca, Mg, pH, soil texture), the system displays them in plain Thai for the farmer to confirm or correct, and only after confirmation calculates a field-specific N-P2O5-K2O fertilizer formula following DLD guidance and replies with a plain village-level Thai explanation.