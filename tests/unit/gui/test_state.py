from datetime import UTC, datetime

from agentle.foundation import new_event_id, new_run_id, new_session_id
from agentle.gui import SessionViewState, ViewStatus, reduce_event
from agentle.runtime import EventKind, RuntimeEvent


def event(
    sequence: int,
    kind: EventKind,
    *,
    session_id=None,
    run_id=None,
    payload=None,
) -> RuntimeEvent:
    return RuntimeEvent(
        event_id=new_event_id(),
        session_id=session_id or new_session_id(),
        run_id=run_id,
        sequence=sequence,
        occurred_at=datetime(2026, 1, 1, tzinfo=UTC),
        kind=kind,
        payload=payload or {},
    )


def test_reducer_streams_and_reconciles_transcript() -> None:
    session_id = new_session_id()
    run_id = new_run_id()
    events = (
        event(1, EventKind.SESSION_CREATED, session_id=session_id),
        event(
            2,
            EventKind.RUN_STARTED,
            session_id=session_id,
            run_id=run_id,
            payload={"prompt": "hello"},
        ),
        event(
            3,
            EventKind.ASSISTANT_DELTA,
            session_id=session_id,
            run_id=run_id,
            payload={"text": "par"},
        ),
        event(
            4,
            EventKind.ASSISTANT_DELTA,
            session_id=session_id,
            run_id=run_id,
            payload={"text": "tial"},
        ),
        event(
            5,
            EventKind.RUN_COMPLETED,
            session_id=session_id,
            run_id=run_id,
            payload={"output": "final"},
        ),
    )
    state = SessionViewState()
    for item in events:
        state = reduce_event(state, item)

    assert [(item.role, item.content) for item in state.transcript] == [
        ("user", "hello"),
        ("assistant", "final"),
    ]
    assert state.status is ViewStatus.IDLE
    assert state.active_run_id is None
    assert reduce_event(state, events[-1]) is state


def test_reducer_detects_gap_and_normalizes_terminal_states() -> None:
    session_id = new_session_id()
    state = reduce_event(
        SessionViewState(), event(1, EventKind.SESSION_CREATED, session_id=session_id)
    )
    gap = reduce_event(
        state,
        event(
            3,
            EventKind.RUN_STARTED,
            session_id=session_id,
            run_id=new_run_id(),
        ),
    )
    assert gap.status is ViewStatus.FAILED
    assert gap.error is not None
    assert gap.error.code == "gui.event_sequence_gap"

    run_id = new_run_id()
    running = reduce_event(
        state,
        event(
            2,
            EventKind.RUN_STARTED,
            session_id=session_id,
            run_id=run_id,
            payload={"prompt": "wait"},
        ),
    )
    cancelled = reduce_event(
        running,
        event(
            3,
            EventKind.RUN_CANCELLED,
            session_id=session_id,
            run_id=run_id,
            payload={"error": {"code": "operation.cancelled", "message": "Cancelled"}},
        ),
    )
    assert cancelled.status is ViewStatus.IDLE
    assert cancelled.active_run_id is None

    failed = reduce_event(
        running,
        event(
            3,
            EventKind.RUN_FAILED,
            session_id=session_id,
            run_id=run_id,
            payload={"error": {"code": "model.unavailable", "message": "Unavailable"}},
        ),
    )
    assert failed.status is ViewStatus.FAILED
    assert failed.error is not None
    assert failed.error.code == "model.unavailable"
