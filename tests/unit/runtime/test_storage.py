from datetime import UTC, datetime

from agentle.foundation import EventId, RunId, SessionId
from agentle.runtime import EventKind, RuntimeEvent, from_stored_event, to_stored_event


def test_runtime_event_storage_mapping_is_canonical_and_reversible() -> None:
    event = RuntimeEvent(
        event_id=EventId("event"),
        session_id=SessionId("session"),
        run_id=RunId("run"),
        sequence=2,
        occurred_at=datetime(2026, 1, 1, tzinfo=UTC),
        kind=EventKind.ASSISTANT_DELTA,
        payload={"z": 1, "text": "héllo"},
    )

    stored = to_stored_event(event)

    assert stored.payload_json == '{"text":"héllo","z":1}'
    assert from_stored_event(stored) == event
