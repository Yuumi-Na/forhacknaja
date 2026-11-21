"""Session storage. In-memory only in this build."""

from __future__ import annotations

from typing import Protocol

from mordin.flows.session import Session


class SessionNotFound(KeyError):
    pass


class SessionStore(Protocol):
    def create(self, s: Session) -> None: ...
    def get(self, session_id: str) -> Session: ...
    def save(self, s: Session) -> None: ...
    def delete(self, session_id: str) -> None: ...


class InMemoryStore:
    """Dict-backed store. Keeps deep copies so callers cannot change stored state by accident."""

    def __init__(self) -> None:
        self._sessions: dict[str, Session] = {}

    def create(self, s: Session) -> None:
        if s.id in self._sessions:
            raise ValueError(f"session {s.id} already exists")
        self._sessions[s.id] = s.model_copy(deep=True)

    def get(self, session_id: str) -> Session:
        try:
            return self._sessions[session_id].model_copy(deep=True)
        except KeyError:
            raise SessionNotFound(session_id) from None

    def save(self, s: Session) -> None:
        if s.id not in self._sessions:
            raise SessionNotFound(s.id)
        self._sessions[s.id] = s.model_copy(deep=True)

    def delete(self, session_id: str) -> None:
        self._sessions.pop(session_id, None)
