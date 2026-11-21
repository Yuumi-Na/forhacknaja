"""หมอดิน AI (Mor Din AI) on AgentCore Runtime.

Thin entrypoint over agent.py. The runtime calls invoke() once per request. Each runtime session runs in its own
microVM, so one agent per session keeps that session's conversation. Reply: {"result": "..."}.
Model: anthropic.claude-sonnet-5 in ap-southeast-1 (guarded in agent.py). Demo values only, no real personal data.
"""
import re
from collections import OrderedDict

from bedrock_agentcore.runtime import BedrockAgentCoreApp

import agent as mordin

app = BedrockAgentCoreApp()
_agents = OrderedDict()  # one agent per runtime session, at most 16 kept


def _get_agent(session_id):
    if session_id not in _agents:
        if len(_agents) >= 16:
            _agents.popitem(last=False)
        _agents[session_id] = mordin.make_agent()
    _agents.move_to_end(session_id)
    return _agents[session_id]


@app.entrypoint
def invoke(payload, context=None):
    prompt = payload.get("prompt", "") if isinstance(payload, dict) else ""
    if not isinstance(prompt, str) or not prompt.strip():
        return {"error": 'Send {"prompt": "..."}'}
    prompt = prompt.strip()
    session_id = getattr(context, "session_id", None) or "local-dev-session-0000000000000000"
    agent = _get_agent(session_id)
    if prompt.lower() in ("restart", "เริ่มใหม่"):
        mordin.reset_session()
        agent.messages.clear()
        return {"result": "เริ่มใหม่แล้วครับ / Started over."}
    mordin.ALLOWED.clear()
    reply = str(agent(prompt)).strip()
    if mordin.unknown_figures(reply):  # a figure no tool gave: replace the reply
        reply = mordin.SAFE_FALLBACK["th" if re.search(r"[ก-๙]", prompt) else "en"]
    return {"result": reply}


if __name__ == "__main__":
    app.run()
