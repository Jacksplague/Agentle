"""Commands accepted by the Agentle application runtime."""

from dataclasses import dataclass, field
from enum import StrEnum

from agentle.foundation import (
    AgentleError,
    CommandId,
    ErrorCategory,
    ErrorInfo,
    RunId,
    SessionId,
    new_command_id,
)


def _validation_error(code: str, message: str) -> AgentleError:
    return AgentleError(ErrorInfo(code=code, category=ErrorCategory.VALIDATION, message=message))


@dataclass(frozen=True, slots=True, kw_only=True)
class CreateSession:
    title: str | None = None
    command_id: CommandId = field(default_factory=new_command_id)

    def __post_init__(self) -> None:
        if self.title is not None and len(self.title) > 200:
            raise _validation_error(
                "runtime.invalid_title", "Session titles are limited to 200 characters."
            )


@dataclass(frozen=True, slots=True, kw_only=True)
class SubmitPrompt:
    session_id: SessionId
    text: str
    agent_id: str
    timeout_seconds: float
    command_id: CommandId = field(default_factory=new_command_id)

    def __post_init__(self) -> None:
        if not self.text.strip():
            raise _validation_error("runtime.empty_prompt", "The prompt must not be empty.")
        if not self.agent_id.strip():
            raise _validation_error("runtime.invalid_agent", "An agent identifier is required.")
        if self.timeout_seconds <= 0:
            raise _validation_error(
                "runtime.invalid_timeout", "The timeout must be greater than zero."
            )


@dataclass(frozen=True, slots=True, kw_only=True)
class CancelRun:
    run_id: RunId
    command_id: CommandId = field(default_factory=new_command_id)


@dataclass(frozen=True, slots=True, kw_only=True)
class Shutdown:
    grace_seconds: float
    command_id: CommandId = field(default_factory=new_command_id)

    def __post_init__(self) -> None:
        if self.grace_seconds < 0:
            raise _validation_error(
                "runtime.invalid_shutdown_grace", "The shutdown grace period cannot be negative."
            )


type RuntimeCommand = CreateSession | SubmitPrompt | CancelRun | Shutdown


class CommandStatus(StrEnum):
    ACCEPTED = "accepted"
    REJECTED = "rejected"


@dataclass(frozen=True, slots=True)
class CommandReceipt:
    command_id: CommandId
    status: CommandStatus
    error: ErrorInfo | None = None
