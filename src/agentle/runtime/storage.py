"""Mapping between Runtime-owned events and Persistence-owned records."""

import json

from agentle.persistence import StoredRuntimeEvent

from .events import EventKind, JsonValue, RuntimeEvent


def to_stored_event(event: RuntimeEvent) -> StoredRuntimeEvent:
    return StoredRuntimeEvent(
        event_id=event.event_id,
        session_id=event.session_id,
        run_id=event.run_id,
        sequence=event.sequence,
        occurred_at=event.occurred_at,
        kind=event.kind.value,
        schema_version=event.schema_version,
        payload_json=json.dumps(
            event.payload,
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        ),
    )


def from_stored_event(event: StoredRuntimeEvent) -> RuntimeEvent:
    payload: dict[str, JsonValue] = json.loads(event.payload_json)
    return RuntimeEvent(
        event_id=event.event_id,
        session_id=event.session_id,
        run_id=event.run_id,
        sequence=event.sequence,
        occurred_at=event.occurred_at,
        kind=EventKind(event.kind),
        schema_version=event.schema_version,
        payload=payload,
    )
