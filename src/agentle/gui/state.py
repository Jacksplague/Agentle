"""Deterministic projection of Runtime events into Phase 1 GUI state."""

from collections.abc import Mapping
from dataclasses import dataclass, replace
from enum import StrEnum

from agentle.foundation import ErrorCategory, ErrorInfo, RunId, SessionId
from agentle.runtime import EventKind, RuntimeEvent


class ViewStatus(StrEnum):
    STARTING = "starting"
    IDLE = "idle"
    RUNNING = "running"
    CANCELLING = "cancelling"
    FAILED = "failed"
    CLOSING = "closing"


@dataclass(frozen=True, slots=True)
class TranscriptItem:
    role: str
    content: str
    run_id: RunId | None = None


@dataclass(frozen=True, slots=True)
class ActivityItem:
    text: str
    run_id: RunId | None = None


@dataclass(frozen=True, slots=True)
class SessionViewState:
    session_id: SessionId | None = None
    last_sequence: int = 0
    transcript: tuple[TranscriptItem, ...] = ()
    activity: tuple[ActivityItem, ...] = ()
    active_run_id: RunId | None = None
    status: ViewStatus = ViewStatus.STARTING
    error: ErrorInfo | None = None


def _string(payload: Mapping[str, object], key: str, default: str = "") -> str:
    value = payload.get(key, default)
    return value if isinstance(value, str) else default


def _replace_assistant(
    transcript: tuple[TranscriptItem, ...], run_id: RunId | None, content: str, *, append: bool
) -> tuple[TranscriptItem, ...]:
    items = list(transcript)
    for index in range(len(items) - 1, -1, -1):
        item = items[index]
        if item.role == "assistant" and item.run_id == run_id:
            value = item.content + content if append else content
            items[index] = replace(item, content=value)
            return tuple(items)
    items.append(TranscriptItem("assistant", content, run_id))
    return tuple(items)


def reduce_event(state: SessionViewState, event: RuntimeEvent) -> SessionViewState:
    if event.sequence <= state.last_sequence:
        return state
    if event.sequence != state.last_sequence + 1:
        return replace(
            state,
            status=ViewStatus.FAILED,
            error=ErrorInfo(
                code="gui.event_sequence_gap",
                category=ErrorCategory.INTERNAL,
                message="The event stream has a gap; reload the session to continue.",
                retryable=True,
            ),
        )
    next_state = replace(state, session_id=event.session_id, last_sequence=event.sequence)
    if event.kind is EventKind.SESSION_CREATED:
        return replace(next_state, status=ViewStatus.IDLE, error=None)
    if event.kind is EventKind.RUN_STARTED:
        transcript = (
            *next_state.transcript,
            TranscriptItem("user", _string(event.payload, "prompt"), event.run_id),
            TranscriptItem("assistant", "", event.run_id),
        )
        return replace(
            next_state,
            transcript=transcript,
            active_run_id=event.run_id,
            status=ViewStatus.RUNNING,
            error=None,
        )
    if event.kind is EventKind.ASSISTANT_DELTA:
        return replace(
            next_state,
            transcript=_replace_assistant(
                next_state.transcript,
                event.run_id,
                _string(event.payload, "text"),
                append=True,
            ),
        )
    if event.kind is EventKind.RUN_COMPLETED:
        return replace(
            next_state,
            transcript=_replace_assistant(
                next_state.transcript,
                event.run_id,
                _string(event.payload, "output"),
                append=False,
            ),
            active_run_id=None,
            status=ViewStatus.IDLE,
        )
    if event.kind in {EventKind.RUN_CANCELLED, EventKind.RUN_FAILED}:
        error_payload = event.payload.get("error")
        error = None
        if isinstance(error_payload, dict):
            error = ErrorInfo(
                code=_string(error_payload, "code", "run.failed"),
                category=(
                    ErrorCategory.CANCELLED
                    if event.kind is EventKind.RUN_CANCELLED
                    else ErrorCategory.INTERNAL
                ),
                message=_string(error_payload, "message", "The run failed."),
            )
        return replace(
            next_state,
            active_run_id=None,
            status=(
                ViewStatus.IDLE
                if event.kind is EventKind.RUN_CANCELLED
                else ViewStatus.FAILED
            ),
            error=error,
        )
    if event.kind in {
        EventKind.TOOL_REQUESTED,
        EventKind.TOOL_STARTED,
        EventKind.TOOL_COMPLETED,
        EventKind.TOOL_FAILED,
    }:
        name = _string(event.payload, "name", "tool")
        activity = ActivityItem(f"{event.kind.value}: {name}", event.run_id)
        return replace(next_state, activity=(*next_state.activity, activity))
    return next_state
