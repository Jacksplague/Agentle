"""Backend-neutral native tool contracts."""

from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol

from agentle.foundation import CancellationToken, Deadline, RunId, SessionId, ToolCallId

type ToolJson = str | int | float | bool | None | list[ToolJson] | dict[str, ToolJson]


class SideEffect(StrEnum):
    READ_ONLY = "read_only"
    WRITE = "write"
    EXECUTE = "execute"


@dataclass(frozen=True, slots=True)
class ToolDefinition:
    name: str
    description: str
    input_schema: dict[str, ToolJson]
    side_effect: SideEffect
    output_media_type: str = "text/plain"


@dataclass(frozen=True, slots=True)
class ToolCall:
    call_id: ToolCallId
    name: str
    arguments: dict[str, ToolJson]


@dataclass(frozen=True, slots=True)
class ToolInvocationContext:
    session_id: SessionId
    run_id: RunId
    workspace: str
    deadline: Deadline
    cancellation: CancellationToken


@dataclass(frozen=True, slots=True)
class ToolResult:
    content: str
    media_type: str
    truncated: bool
    metadata: dict[str, ToolJson]


class Tool(Protocol):
    @property
    def definition(self) -> ToolDefinition: ...

    async def invoke(self, call: ToolCall, context: ToolInvocationContext) -> ToolResult: ...
