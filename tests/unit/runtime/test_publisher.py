from datetime import UTC, datetime

import pytest

from agentle.foundation import AgentleError, EventId, SessionId
from agentle.runtime import EventKind, EventPublisher, RuntimeEvent


def make_event(sequence: int) -> RuntimeEvent:
    return RuntimeEvent(
        event_id=EventId(f"event-{sequence}"),
        session_id=SessionId("session"),
        sequence=sequence,
        occurred_at=datetime(2026, 1, 1, tzinfo=UTC),
        kind=EventKind.SESSION_CREATED,
        payload={},
    )


async def test_publisher_preserves_order() -> None:
    publisher = EventPublisher(subscriber_capacity=2)
    subscription = publisher.subscribe()

    publisher.publish(make_event(1))
    publisher.publish(make_event(2))

    assert (await subscription.get()).sequence == 1
    assert (await subscription.get()).sequence == 2


async def test_slow_subscriber_is_disconnected_and_can_drain_committed_events() -> None:
    publisher = EventPublisher(subscriber_capacity=1)
    subscription = publisher.subscribe()

    publisher.publish(make_event(1))
    publisher.publish(make_event(2))

    assert (await subscription.get()).sequence == 1
    with pytest.raises(AgentleError) as caught:
        await subscription.get()

    assert caught.value.info.code == "runtime.subscriber_slow"
