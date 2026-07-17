"""Storage-facing records and explicit repository protocols."""

import json
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import NewType, Protocol
from uuid import uuid4

from agentle.foundation import ErrorInfo, EventId, RunId, SessionId, as_utc

MessageId = NewType("MessageId", str)


def new_message_id() -> MessageId:
    return MessageId(str(uuid4()))


class MessageRole(StrEnum):
    USER = "user"
    ASSISTANT = "assistant"


class RunStatus(StrEnum):
    STARTED = "started"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass(frozen=True, slots=True)
class SessionRecord:
    session_id: SessionId
    title: str | None
    created_at: datetime
    updated_at: datetime

    def __post_init__(self) -> None:
        object.__setattr__(self, "created_at", as_utc(self.created_at))
        object.__setattr__(self, "updated_at", as_utc(self.updated_at))


@dataclass(frozen=True, slots=True)
class MessageRecord:
    message_id: MessageId
    session_id: SessionId
    role: MessageRole
    content: str
    created_at: datetime
    run_id: RunId | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "created_at", as_utc(self.created_at))


@dataclass(frozen=True, slots=True)
class RunRecord:
    run_id: RunId
    session_id: SessionId
    agent_id: str
    model_id: str
    status: RunStatus
    started_at: datetime
    finished_at: datetime | None = None
    error: ErrorInfo | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "started_at", as_utc(self.started_at))
        if self.finished_at is not None:
            object.__setattr__(self, "finished_at", as_utc(self.finished_at))


@dataclass(frozen=True, slots=True)
class StoredRuntimeEvent:
    event_id: EventId
    session_id: SessionId
    sequence: int
    occurred_at: datetime
    kind: str
    schema_version: int
    payload_json: str
    run_id: RunId | None = None

    def __post_init__(self) -> None:
        if self.sequence < 1:
            raise ValueError("stored event sequence must be positive")
        object.__setattr__(self, "occurred_at", as_utc(self.occurred_at))
        payload = json.loads(self.payload_json)
        if not isinstance(payload, dict):
            raise ValueError("stored event payload must be a JSON object")


class SessionRepository(Protocol):
    async def create_session(
        self, session: SessionRecord, created_event: StoredRuntimeEvent
    ) -> None: ...

    async def get_session(self, session_id: SessionId) -> SessionRecord | None: ...

    async def list_messages(self, session_id: SessionId) -> list[MessageRecord]: ...


class RunJournal(Protocol):
    async def start_run(
        self,
        run: RunRecord,
        user_message: MessageRecord,
        started_event: StoredRuntimeEvent,
    ) -> None: ...

    async def append_event(self, event: StoredRuntimeEvent) -> None: ...

    async def complete_run(
        self,
        run_id: RunId,
        assistant_message: MessageRecord,
        terminal_event: StoredRuntimeEvent,
    ) -> None: ...

    async def terminate_run(
        self,
        run_id: RunId,
        status: RunStatus,
        terminal_event: StoredRuntimeEvent,
        error: ErrorInfo | None,
    ) -> None: ...

    async def get_run(self, run_id: RunId) -> RunRecord | None: ...

    async def list_events(
        self, session_id: SessionId, after_sequence: int = 0
    ) -> list[StoredRuntimeEvent]: ...

    async def last_sequence(self, session_id: SessionId) -> int: ...

    async def list_incomplete_runs(self) -> list[RunRecord]: ...


class Persistence(SessionRepository, RunJournal, Protocol):
    async def close(self) -> None: ...
