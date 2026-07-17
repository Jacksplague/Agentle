"""Dependency-light contracts shared by Agentle sections."""

from .cancellation import CancellationSource, CancellationToken
from .errors import AgentleError, ErrorCategory, ErrorDetail, ErrorInfo, error_info_from_exception
from .identifiers import (
    CommandId,
    EventId,
    ExecutionId,
    RunId,
    SessionId,
    ToolCallId,
    new_command_id,
    new_event_id,
    new_execution_id,
    new_run_id,
    new_session_id,
    new_tool_call_id,
)
from .secrets import EnvironmentSecretResolver, SecretRef, SecretResolver
from .time import Clock, Deadline, SystemClock, as_utc

__all__ = [
    "AgentleError",
    "CancellationSource",
    "CancellationToken",
    "Clock",
    "CommandId",
    "Deadline",
    "EnvironmentSecretResolver",
    "ErrorCategory",
    "ErrorDetail",
    "ErrorInfo",
    "EventId",
    "ExecutionId",
    "RunId",
    "SecretRef",
    "SecretResolver",
    "SessionId",
    "SystemClock",
    "ToolCallId",
    "as_utc",
    "error_info_from_exception",
    "new_command_id",
    "new_event_id",
    "new_execution_id",
    "new_run_id",
    "new_session_id",
    "new_tool_call_id",
]
