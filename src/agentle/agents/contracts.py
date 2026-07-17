"""Single-agent definitions, run inputs, events, and runner protocol."""

from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Protocol

from agentle.context import AssembledContext
from agentle.foundation import (
    CancellationToken,
    Deadline,
    ErrorInfo,
    RunId,
    SessionId,
    ToolCallId,
)
from agentle.models import ModelBinding
from agentle.tools import ToolInvoker, ToolJson


@dataclass(frozen=True, slots=True)
class AgentDefinition:
    agent_id: str
    display_name: str
    instructions: str
    model_id: str
    allowed_tools: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.agent_id.strip() or not self.display_name.strip():
            raise ValueError("agent identifiers must not be empty")
        if not self.instructions.strip():
            raise ValueError("agent instructions must not be empty")
        if not self.model_id.strip():
            raise ValueError("an agent model identifier is required")
        if len(set(self.allowed_tools)) != len(self.allowed_tools):
            raise ValueError("agent tool allow-list contains duplicates")


@dataclass(frozen=True, slots=True)
class AgentRunInput:
    session_id: SessionId
    run_id: RunId
    definition: AgentDefinition
    context: AssembledContext
    model: ModelBinding
    tool_invoker: ToolInvoker
    workspace: str
    deadline: Deadline
    cancellation: CancellationToken


@dataclass(frozen=True, slots=True)
class TextDelta:
    text: str


@dataclass(frozen=True, slots=True)
class ToolRequested:
    call_id: ToolCallId
    name: str
    arguments: dict[str, ToolJson]


@dataclass(frozen=True, slots=True)
class ToolStarted:
    call_id: ToolCallId
    name: str


@dataclass(frozen=True, slots=True)
class ToolCompleted:
    call_id: ToolCallId
    name: str
    truncated: bool


@dataclass(frozen=True, slots=True)
class ToolFailed:
    call_id: ToolCallId
    name: str
    error: ErrorInfo


@dataclass(frozen=True, slots=True)
class UsageUpdated:
    input_tokens: int | None = None
    output_tokens: int | None = None


@dataclass(frozen=True, slots=True)
class FinalOutput:
    output: str


type AgentRunEvent = (
    TextDelta
    | ToolRequested
    | ToolStarted
    | ToolCompleted
    | ToolFailed
    | UsageUpdated
    | FinalOutput
)


class AgentRunner(Protocol):
    @property
    def runner_family(self) -> str: ...

    def run(self, run_input: AgentRunInput) -> AsyncIterator[AgentRunEvent]: ...

    async def close(self) -> None: ...
