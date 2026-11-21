"""Events, commands and reply specs for the pure reducer. No I/O, no farmer-facing text."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from mordin.flows.session import Session, SheetItem, SoilValue


# --- Events -----------------------------------------------------------------
@dataclass(frozen=True)
class Text:
    text: str


@dataclass(frozen=True)
class Button:
    action: str
    payload: str | None = None


@dataclass(frozen=True)
class ImageUploaded:
    filename: str


@dataclass(frozen=True)
class ReadSucceeded:
    """Vision result: soil values (None = unreadable) and the sheet's recommendations."""

    values: dict[str, SoilValue] = field(default_factory=dict)
    sheet_recommendations: list[SheetItem] = field(default_factory=list)
    is_dld_sheet: bool = True
    unreadable: dict[str, str] = field(default_factory=dict)  # field -> reason


@dataclass(frozen=True)
class ReadFailed:
    reason: str = ""


@dataclass(frozen=True)
class Explained:
    """Advice built by explain/: table, shop script and explanation, as data."""

    advice: Any


@dataclass(frozen=True)
class ExplainFailed:
    reason: str = ""


@dataclass(frozen=True)
class AgentReplied:
    """Reply text from the deployed chat agent. Shown as is, never used for any calculation."""
    text: str


@dataclass(frozen=True)
class AgentFailed:
    reason: str = ""


Event = (
    Text | Button | ImageUploaded | ReadSucceeded | ReadFailed | Explained | ExplainFailed
    | AgentReplied | AgentFailed
)


# --- Commands ---------------------------------------------------------------
@dataclass(frozen=True)
class ReadImage:
    filename: str


@dataclass(frozen=True)
class BuildAdvice:
    pass


@dataclass(frozen=True)
class AskAgent:
    """Send typed text that answers no pending step to the deployed agent."""
    text: str


Command = ReadImage | BuildAdvice | AskAgent


# --- Reply specs ------------------------------------------------------------
@dataclass(frozen=True)
class ButtonSpec:
    """A button the page shows. `label_key` is a message key, not text."""

    label_key: str
    action: str
    payload: str | None = None
    params: dict[str, Any] = field(default_factory=dict)  # for the label text


@dataclass(frozen=True)
class Reply:
    """A message spec. `key` is looked up in explain/messages.py."""

    key: str
    params: dict[str, Any] = field(default_factory=dict)
    buttons: list[ButtonSpec] = field(default_factory=list)


@dataclass(frozen=True)
class Step:
    session: Session
    replies: list[Reply] = field(default_factory=list)
    commands: list[Command] = field(default_factory=list)
