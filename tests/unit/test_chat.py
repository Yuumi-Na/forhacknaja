import io
import json

import pytest

from mordin import config
from mordin.data import load_data
from mordin.explain.chat import AgentError, ask_agent, runtime_session_id
from mordin.flows import Button, ImageUploaded, State, Text
from mordin.flows.session import Session
from mordin.flows.types import AgentFailed, AgentReplied, AskAgent
from mordin.flows.reducer import reduce
from mordin.service import Service
from mordin.storage.store import InMemoryStore

ARN = "arn:aws:bedrock-agentcore:ap-southeast-1:123456789012:runtime/Demo_Agent-abc"
DATA = load_data()


class FakeClient:
    def __init__(self, body: bytes = b'{"result": "  hello  "}', error: Exception | None = None):
        self.body, self.error, self.calls = body, error, []

    def invoke_agent_runtime(self, **kwargs):
        self.calls.append(kwargs)
        if self.error:
            raise self.error
        return {"contentType": "application/json", "response": io.BytesIO(self.body)}


@pytest.fixture
def arn_env(monkeypatch):
    monkeypatch.setenv(config.AGENT_RUNTIME_ARN_ENV, ARN)


def test_sends_prompt_and_returns_reply(arn_env):
    client = FakeClient()
    assert ask_agent("  สวัสดี  ", "a" * 32, client=client) == "hello"
    call = client.calls[0]
    assert call["agentRuntimeArn"] == ARN
    assert json.loads(call["payload"]) == {"prompt": "สวัสดี"}
    assert len(call["runtimeSessionId"]) >= 33
    assert call["runtimeSessionId"] == runtime_session_id("a" * 32)


def test_event_stream_reply_is_read(arn_env):
    client = FakeClient(body=b'data: {"result": "hi"}\n\n')
    assert ask_agent("x", "s", client=client) == "hi"


@pytest.mark.parametrize("body", [b"not json", b'{"error": "Send prompt"}', b'{"result": "  "}', b"[]"])
def test_bad_reply_raises(arn_env, body):
    with pytest.raises(AgentError):
        ask_agent("x", "s", client=FakeClient(body=body))


def test_client_error_becomes_agent_error(arn_env):
    with pytest.raises(AgentError):
        ask_agent("x", "s", client=FakeClient(error=RuntimeError("boom")))


def test_empty_text_makes_no_call(arn_env):
    client = FakeClient()
    with pytest.raises(AgentError):
        ask_agent("   ", "s", client=client)
    assert client.calls == []


def test_arn_must_be_set_and_in_region(monkeypatch):
    monkeypatch.delenv(config.AGENT_RUNTIME_ARN_ENV, raising=False)
    with pytest.raises(config.ConfigError):
        config.agent_runtime_arn()
    monkeypatch.setenv(config.AGENT_RUNTIME_ARN_ENV, ARN.replace("ap-southeast-1", "us-west-2"))
    with pytest.raises(config.ConfigError):
        config.agent_runtime_arn()


# --- flow -------------------------------------------------------------------------------


def test_text_with_no_pending_step_asks_the_agent():
    step = reduce(Session(), Text("ปุ๋ยยูเรียคืออะไร"), DATA)
    assert step.commands == [AskAgent("ปุ๋ยยูเรียคืออะไร")]


def test_blank_text_does_not_ask_the_agent():
    step = reduce(Session(), Text("   "), DATA)
    assert step.commands == [] and step.replies[0].key == "input.choose_button"


def test_area_answer_never_goes_to_the_agent():
    svc = Service(InMemoryStore(), DATA, stub=True, agent_caller=lambda t, s: "AGENT")
    sid = svc.start()["session_id"]
    svc.handle(sid, ImageUploaded("demo_sheet_ok.jpg"))
    svc.handle(sid, Button("confirm"))
    out = svc.handle(sid, Text("5"))
    assert out["state"] == State.RESULT_SENT.value
    assert "AGENT" not in " ".join(b["text"] for b in out["bubbles"])


def test_service_shows_agent_reply_and_keeps_state():
    seen = []
    svc = Service(InMemoryStore(), DATA, stub=True, agent_caller=lambda t, s: seen.append((t, s)) or "ตอบแล้ว")
    sid = svc.start()["session_id"]
    out = svc.handle(sid, Text("ถามหน่อย"))
    assert out["bubbles"] == [{"kind": "text", "text": "ตอบแล้ว", "buttons": []}]
    assert out["state"] == svc.store.get(sid).state.value
    assert seen == [("ถามหน่อย", sid)]


def test_agent_failure_falls_back_to_the_fixed_reply():
    def boom(text, session_id):
        raise AgentError("down")

    svc = Service(InMemoryStore(), DATA, stub=True, agent_caller=boom)
    sid = svc.start()["session_id"]
    out = svc.handle(sid, Text("ถามหน่อย"))
    assert len(out["bubbles"]) == 1 and "กรุณากดปุ่ม" in out["bubbles"][0]["text"]


def test_stub_service_has_no_agent():
    svc = Service(InMemoryStore(), DATA, stub=True)
    assert svc.agent_caller is None
    out = svc.handle(svc.start()["session_id"], Text("ถามหน่อย"))
    assert "กรุณากดปุ่ม" in out["bubbles"][0]["text"]


def test_agent_events_do_not_change_the_session():
    s = Session()
    for ev in (AgentReplied("x"), AgentFailed("y")):
        assert reduce(s, ev, DATA).session.state == s.state
