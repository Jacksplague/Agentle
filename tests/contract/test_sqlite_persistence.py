from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from agentle.foundation import (
    AgentleError,
    ErrorCategory,
    ErrorInfo,
    EventId,
    RunId,
    SessionId,
)
from agentle.persistence import (
    MessageRecord,
    MessageRole,
    RunRecord,
    RunStatus,
    SessionRecord,
    SQLitePersistence,
    StoredRuntimeEvent,
    new_message_id,
)

NOW = datetime(2026, 1, 1, tzinfo=UTC)


def event(
    session_id: SessionId,
    sequence: int,
    kind: str,
    *,
    run_id: RunId | None = None,
) -> StoredRuntimeEvent:
    return StoredRuntimeEvent(
        event_id=EventId(f"event-{sequence}"),
        session_id=session_id,
        run_id=run_id,
        sequence=sequence,
        occurred_at=NOW + timedelta(seconds=sequence),
        kind=kind,
        schema_version=1,
        payload_json="{}",
    )


async def create_session(
    persistence: SQLitePersistence, session_id: SessionId
) -> SessionRecord:
    session = SessionRecord(
        session_id=session_id,
        title="Contract test",
        created_at=NOW,
        updated_at=NOW,
    )
    await persistence.create_session(session, event(session_id, 1, "session.created"))
    return session


async def test_complete_run_is_durable_and_replayable(tmp_path: Path) -> None:
    database = tmp_path / "agentle.sqlite3"
    session_id = SessionId("session")
    run_id = RunId("run")
    persistence = await SQLitePersistence.open(database)
    session = await create_session(persistence, session_id)
    run = RunRecord(
        run_id=run_id,
        session_id=session_id,
        agent_id="default",
        model_id="test-model",
        status=RunStatus.STARTED,
        started_at=NOW + timedelta(seconds=2),
    )
    user_message = MessageRecord(
        message_id=new_message_id(),
        session_id=session_id,
        run_id=run_id,
        role=MessageRole.USER,
        content="hello",
        created_at=run.started_at,
    )
    await persistence.start_run(
        run, user_message, event(session_id, 2, "run.started", run_id=run_id)
    )
    await persistence.append_event(event(session_id, 3, "assistant.delta", run_id=run_id))
    assistant_message = MessageRecord(
        message_id=new_message_id(),
        session_id=session_id,
        run_id=run_id,
        role=MessageRole.ASSISTANT,
        content="world",
        created_at=NOW + timedelta(seconds=4),
    )
    await persistence.complete_run(
        run_id,
        assistant_message,
        event(session_id, 4, "run.completed", run_id=run_id),
    )

    assert await persistence.get_session(session_id) == SessionRecord(
        session_id=session_id,
        title=session.title,
        created_at=session.created_at,
        updated_at=NOW + timedelta(seconds=4),
    )
    assert [message.content for message in await persistence.list_messages(session_id)] == [
        "hello",
        "world",
    ]
    completed = await persistence.get_run(run_id)
    assert completed is not None
    assert completed.status is RunStatus.COMPLETED
    assert completed.finished_at == NOW + timedelta(seconds=4)
    assert [item.sequence for item in await persistence.list_events(session_id)] == [1, 2, 3, 4]
    await persistence.close()

    reopened = await SQLitePersistence.open(database)
    assert [item.kind for item in await reopened.list_events(session_id, after_sequence=2)] == [
        "assistant.delta",
        "run.completed",
    ]
    assert [message.content for message in await reopened.list_messages(session_id)] == [
        "hello",
        "world",
    ]
    await reopened.close()


async def test_out_of_order_event_rolls_back_without_advancing_sequence(tmp_path: Path) -> None:
    persistence = await SQLitePersistence.open(tmp_path / "ordering.sqlite3")
    session_id = SessionId("session")
    await create_session(persistence, session_id)

    with pytest.raises(AgentleError) as caught:
        await persistence.append_event(event(session_id, 3, "assistant.delta", run_id=RunId("run")))

    assert caught.value.info.code == "persistence.event_order"
    assert await persistence.last_sequence(session_id) == 1
    await persistence.close()


async def test_failed_start_is_atomic(tmp_path: Path) -> None:
    persistence = await SQLitePersistence.open(tmp_path / "atomic.sqlite3")
    session_id = SessionId("session")
    run_id = RunId("run")
    await create_session(persistence, session_id)
    run = RunRecord(
        run_id=run_id,
        session_id=session_id,
        agent_id="default",
        model_id="test-model",
        status=RunStatus.STARTED,
        started_at=NOW,
    )
    message = MessageRecord(
        message_id=new_message_id(),
        session_id=session_id,
        run_id=run_id,
        role=MessageRole.USER,
        content="hello",
        created_at=NOW,
    )

    with pytest.raises(AgentleError):
        await persistence.start_run(
            run, message, event(session_id, 3, "run.started", run_id=run_id)
        )

    assert await persistence.get_run(run_id) is None
    assert await persistence.list_messages(session_id) == []
    assert await persistence.last_sequence(session_id) == 1
    await persistence.close()


async def test_terminal_error_round_trips_and_connection_closes(tmp_path: Path) -> None:
    database = tmp_path / "failed.sqlite3"
    persistence = await SQLitePersistence.open(database)
    session_id = SessionId("session")
    run_id = RunId("run")
    await create_session(persistence, session_id)
    run = RunRecord(
        run_id=run_id,
        session_id=session_id,
        agent_id="default",
        model_id="test-model",
        status=RunStatus.STARTED,
        started_at=NOW,
    )
    message = MessageRecord(
        message_id=new_message_id(),
        session_id=session_id,
        run_id=run_id,
        role=MessageRole.USER,
        content="hello",
        created_at=NOW,
    )
    await persistence.start_run(run, message, event(session_id, 2, "run.started", run_id=run_id))
    failure = ErrorInfo(
        code="provider.unavailable",
        category=ErrorCategory.PROVIDER,
        message="Provider unavailable.",
        retryable=True,
    )
    await persistence.terminate_run(
        run_id,
        RunStatus.FAILED,
        event(session_id, 3, "run.failed", run_id=run_id),
        failure,
    )

    stored = await persistence.get_run(run_id)
    assert stored is not None
    assert stored.error == failure
    assert await persistence.list_incomplete_runs() == []
    await persistence.close()

    reopened = await SQLitePersistence.open(database)
    await reopened.close()
