import re
from pathlib import Path

from mordin.flows import (
    BuildAdvice,
    Button,
    ButtonSpec,
    ImageUploaded,
    ReadImage,
    Reply,
    Session,
    Step,
)


def test_step_defaults_and_reply_spec():
    s = Session()
    reply = Reply(key="retake.message", params={"part": "ph"}, buttons=[ButtonSpec("btn.manual", "manual")])
    step = Step(session=s, replies=[reply], commands=[ReadImage("a.jpg"), BuildAdvice()])
    assert step.session is s
    assert step.replies[0].buttons[0].action == "manual"
    assert Step(session=s).replies == [] and Step(session=s).commands == []
    assert Button("confirm").payload is None
    assert ImageUploaded("a.jpg").filename == "a.jpg"


def test_no_thai_text_in_flows():
    flows = Path(__file__).resolve().parents[2] / "src" / "mordin" / "flows"
    for path in flows.glob("*.py"):
        assert not re.search(r"[\u0E00-\u0E7F]", path.read_text(encoding="utf-8")), path.name
