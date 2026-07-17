"""Backend-independent runtime event contracts."""

import json
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from agentle.foundation import EventId, RunId, SessionId, as_utc

type JsonValue = str | int | float | bool | None | list[JsonValue] | dict[str, JsonValue]


class EventKind(StrEnum):
    SESSION_CREATED = "session.created"
    RUN_STARTED = "run.started"
    ASSISTANT_DELTA = "assistant.delta"
    TOOL_REQUESTED = "tool.requested"
    TOOL_STARTED = "tool.started"
    TOOL_COMPLETED = "tool.completed"
    TOOL_FAILED = "tool.failed"
    EXECUTION_STARTED = "execution.started"
    EXECUTION_OUTPUT = "execution.output"
    EXECUTION_COMPLETED = "execution.completed"
    EXECUTION_FAILED = "execution.failed"
    RUN_COMPLETED = "run.completed"
    RUN_CANCELLED = "run.cancelled"
    RUN_FAILED = "run.failed"


TERMINAL_EVENT_KINDS = frozenset(
    {EventKind.RUN_COMPLETED, EventKind.RUN_CANCELLED, EventKind.RUN_FAILED}
)


@dataclass(frozen=True, slots=True)
class RuntimeEvent:
    event_id: EventId
    session_id: SessionId
    sequence: int
    occurred_at: datetime
    kind: EventKind
    payload: dict[str, JsonValue]
    run_id: RunId | None = None
    schema_version: int = 1

    def __post_init__(self) -> None:
        if self.sequence < 1:
            raise ValueError("event sequence must be positive")
        if self.schema_version != 1:
            raise ValueError("unsupported runtime event schema version")
        object.__setattr__(self, "occurred_at", as_utc(self.occurred_at))
        json.dumps(self.payload, allow_nan=False)
        if self.kind is not EventKind.SESSION_CREATED and self.run_id is None:
            raise ValueError("run events require a run identifier")

    @property
    def terminal(self) -> bool:
        return self.kind in TERMINAL_EVENT_KINDS
