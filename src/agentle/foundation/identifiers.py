"""Opaque identifiers shared by Agentle boundary contracts."""

from typing import NewType
from uuid import uuid4

SessionId = NewType("SessionId", str)
RunId = NewType("RunId", str)
CommandId = NewType("CommandId", str)
EventId = NewType("EventId", str)
ToolCallId = NewType("ToolCallId", str)
ExecutionId = NewType("ExecutionId", str)

def new_session_id() -> SessionId:
    return SessionId(str(uuid4()))


def new_run_id() -> RunId:
    return RunId(str(uuid4()))


def new_command_id() -> CommandId:
    return CommandId(str(uuid4()))


def new_event_id() -> EventId:
    return EventId(str(uuid4()))


def new_tool_call_id() -> ToolCallId:
    return ToolCallId(str(uuid4()))


def new_execution_id() -> ExecutionId:
    return ExecutionId(str(uuid4()))
