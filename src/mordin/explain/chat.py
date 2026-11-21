"""Send the user's text to the agent deployed on AgentCore Runtime and return its reply.

The call uses the bedrock-agentcore InvokeAgentRuntime API in ap-southeast-1. Credentials come from
the default AWS chain (`aws login`, role, environment). None are read or stored here. Importing this
module needs no credentials or network: boto3 is imported inside `ask_agent`.
"""
from __future__ import annotations

import json
from typing import Any

from mordin import config

MAX_TEXT_CHARS = 2000
_MIN_SESSION_ID_CHARS = 33  # InvokeAgentRuntime needs runtimeSessionId of at least 33 characters


class AgentError(Exception):
    """The deployed agent could not be reached or gave no usable reply."""


def runtime_session_id(session_id: str) -> str:
    """Stable runtime session id for one app session (the app's ids are 32 characters)."""
    rid = f"mordin-{session_id}"
    return rid.ljust(_MIN_SESSION_ID_CHARS, "0")


def _reply_from_body(body: str) -> str:
    """Read {"result": "..."} from a JSON body, or from the data lines of an event stream."""
    lines = [ln[6:] for ln in body.splitlines() if ln.startswith("data: ")]
    raw = "\n".join(lines) if lines else body
    try:
        parsed: Any = json.loads(raw)
    except ValueError as exc:
        raise AgentError("reply is not JSON") from exc
    if isinstance(parsed, str):
        text = parsed
    elif isinstance(parsed, dict) and isinstance(parsed.get("result"), str):
        text = parsed["result"]
    else:
        raise AgentError("reply has no result")
    if not text.strip():
        raise AgentError("empty reply")
    return text.strip()


def ask_agent(text: str, session_id: str, *, client: Any = None) -> str:
    """Send `text` to the deployed agent and return its reply text.

    `session_id` is the app session id. The same id reaches the same runtime session, so the agent
    keeps the conversation. Raises AgentError (or ConfigError for a bad ARN setting) on any failure.
    """
    prompt = text.strip()[:MAX_TEXT_CHARS]
    if not prompt:
        raise AgentError("empty text")
    arn = config.agent_runtime_arn()
    try:
        if client is None:
            import boto3
            from botocore.config import Config as BotocoreConfig

            client = boto3.client(
                "bedrock-agentcore",
                region_name=config.REGION,
                config=BotocoreConfig(
                    connect_timeout=5,
                    read_timeout=config.AGENT_READ_TIMEOUT_SECONDS,
                    retries={"max_attempts": 2, "mode": "standard"},
                ),
            )
        response = client.invoke_agent_runtime(
            agentRuntimeArn=arn,
            runtimeSessionId=runtime_session_id(session_id),
            contentType="application/json",
            accept="application/json",
            payload=json.dumps({"prompt": prompt}).encode("utf-8"),
        )
        body = response["response"].read().decode("utf-8")
    except AgentError:
        raise
    except Exception as exc:  # network, permission, throttle, missing field
        raise AgentError(type(exc).__name__) from exc
    return _reply_from_body(body)
