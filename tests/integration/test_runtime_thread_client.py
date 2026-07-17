import threading
from pathlib import Path

import pytest

from agentle.foundation import ErrorInfo
from agentle.runtime import (
    CommandReceipt,
    CreateSession,
    EventKind,
    RuntimeEvent,
    RuntimeThreadClient,
    Shutdown,
)
from tests.integration.test_runtime_vertical_core import make_runtime

pytestmark = pytest.mark.integration


def test_runtime_thread_starts_forwards_events_and_stops(tmp_path: Path) -> None:
    ready = threading.Event()
    created = threading.Event()
    stopped = threading.Event()
    receipts: list[CommandReceipt] = []
    errors: list[ErrorInfo] = []

    async def factory():  # type: ignore[no-untyped-def]
        service, _, _, _ = await make_runtime(tmp_path)
        return service

    def on_event(event: RuntimeEvent) -> None:
        if event.kind is EventKind.SESSION_CREATED:
            created.set()

    client = RuntimeThreadClient(
        factory,
        on_ready=ready.set,
        on_receipt=receipts.append,
        on_event=on_event,
        on_snapshot=lambda _snapshot: None,
        on_error=errors.append,
        on_stopped=stopped.set,
    )
    client.start()
    assert ready.wait(2)
    client.submit(CreateSession(title="Threaded"))
    assert created.wait(2)
    client.submit(Shutdown(grace_seconds=1))
    assert stopped.wait(2)
    assert client.join(1)
    assert not client.alive
    assert len(receipts) == 2
    assert errors == []
