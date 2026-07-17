from datetime import UTC, datetime

import pytest

from agentle.foundation import EventId, RunId, SessionId
from agentle.runtime import EventKind, RuntimeEvent


def test_runtime_event_is_normalized_and_terminal_state_is_explicit() -> None:
    event = RuntimeEvent(
        event_id=EventId("event"),
        session_id=SessionId("session"),
        run_id=RunId("run"),
        sequence=3,
        occurred_at=datetime(2026, 1, 1, tzinfo=UTC),
        kind=EventKind.RUN_COMPLETED,
        payload={"output": "done"},
    )

    assert event.schema_version == 1
    assert event.terminal


def test_non_session_event_requires_run_id() -> None:
    with pytest.raises(ValueError, match="run identifier"):
        RuntimeEvent(
            event_id=EventId("event"),
            session_id=SessionId("session"),
            sequence=1,
            occurred_at=datetime(2026, 1, 1, tzinfo=UTC),
            kind=EventKind.RUN_STARTED,
            payload={},
        )


def test_event_rejects_invalid_sequence_and_non_json_payload() -> None:
    with pytest.raises(ValueError, match="positive"):
        RuntimeEvent(
            event_id=EventId("event"),
            session_id=SessionId("session"),
            sequence=0,
            occurred_at=datetime(2026, 1, 1, tzinfo=UTC),
            kind=EventKind.SESSION_CREATED,
            payload={},
        )

    with pytest.raises(TypeError):
        RuntimeEvent(  # type: ignore[arg-type]
            event_id=EventId("event"),
            session_id=SessionId("session"),
            sequence=1,
            occurred_at=datetime(2026, 1, 1, tzinfo=UTC),
            kind=EventKind.SESSION_CREATED,
            payload={"not_json": object()},
        )
