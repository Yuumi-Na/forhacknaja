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

## Chat agent on AgentCore Runtime
Typed text that does not answer a pending step (field size, manual values, a correction) goes to the agent deployed on AgentCore Runtime. The call is `InvokeAgentRuntime` in `ap-southeast-1` (`src/mordin/explain/chat.py`). It uses your normal AWS sign-in (`aws login`). No credentials are in the code.

Set the runtime ARN (shown by `agentcore status` in `MordinCloud/`) before you start the app:
```
$env:MORDIN_AGENT_RUNTIME_ARN = "arn:aws:bedrock-agentcore:ap-southeast-1:<account>:runtime/<runtime id>"
```
If the ARN is not set, the agent is unreachable or the stub switch is on, the app shows the fixed "please press a button" reply.

## Flows


- **A. Lab sheet photo:** the AI reads the soil values and the fertilizer formula and rate printed on the sheet. The farmer confirms or edits them, then gives the field size. The sheet's rate is multiplied by the field size, not recalculated.
- **B. Manual, full values:** the farmer types soil values. The basic sugarcane formula gives the rate, then the totals for the field.
- **C. Manual, pH only:** the pH class (acidic, balanced, alkaline) gives a first-step soil improvement material and amount. A lab soil test is recommended.

## Warnings

- **Demo data only.** Fertilizer prices, the basic formula rules and the soil amendment table are placeholder demo values. They are not real DLD guidance. Do not use them for real purchase decisions.
- **AI reading accuracy has not been validated** against the lab sheet test set.

## Other

- `agent.py` is a separate starter demo agent, not part of this app.
