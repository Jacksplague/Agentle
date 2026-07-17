import os
from datetime import UTC, datetime

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtWidgets import QApplication

from agentle.foundation import SessionId, new_event_id, new_run_id, new_session_id
from agentle.gui.main_window import MainWindow
from agentle.runtime import EventKind, RuntimeEvent

pytestmark = pytest.mark.gui


class FakeRuntimeClient(QObject):
    ready = pyqtSignal()
    event_received = pyqtSignal(object)
    error_received = pyqtSignal(object)
    stopped = pyqtSignal()

    def __init__(self) -> None:
        super().__init__()
        self.worker_alive = True
        self.created = False
        self.prompts: list[tuple[SessionId, str]] = []
        self.shutdown_requested = False

    def start(self) -> None:
        self.ready.emit()

    def create_session(self, title: str | None = None) -> None:
        self.created = True

    def submit_prompt(self, session_id: SessionId, text: str) -> None:
        self.prompts.append((session_id, text))

    def cancel_run(self, run_id: object) -> None:
        return None

    def shutdown(self, grace_seconds: float = 5) -> None:
        self.shutdown_requested = True


def runtime_event(
    sequence: int,
    kind: EventKind,
    session_id: SessionId,
    *,
    run_id=None,
    payload=None,
) -> RuntimeEvent:
    return RuntimeEvent(
        event_id=new_event_id(),
        session_id=session_id,
        run_id=run_id,
        sequence=sequence,
        occurred_at=datetime(2026, 1, 1, tzinfo=UTC),
        kind=kind,
        payload=payload or {},
    )


def test_offscreen_window_submits_and_renders_without_backends() -> None:
    application = QApplication.instance() or QApplication([])
    client = FakeRuntimeClient()
    window = MainWindow(client)  # type: ignore[arg-type]
    window.show()
    window.start()
    application.processEvents()
    assert client.created

    session_id = new_session_id()
    run_id = new_run_id()
    client.event_received.emit(runtime_event(1, EventKind.SESSION_CREATED, session_id))
    application.processEvents()
    window.prompt.setPlainText("hello")
    window.send_button.click()
    assert client.prompts == [(session_id, "hello")]

    client.event_received.emit(
        runtime_event(
            2,
            EventKind.RUN_STARTED,
            session_id,
            run_id=run_id,
            payload={"prompt": "hello"},
        )
    )
    client.event_received.emit(
        runtime_event(
            3,
            EventKind.ASSISTANT_DELTA,
            session_id,
            run_id=run_id,
            payload={"text": "world"},
        )
    )
    client.event_received.emit(
        runtime_event(
            4,
            EventKind.RUN_COMPLETED,
            session_id,
            run_id=run_id,
            payload={"output": "world"},
        )
    )
    application.processEvents()
    assert "Assistant: world" in window.transcript.toPlainText()
    assert window.send_button.isEnabled()

    window.close()
    application.processEvents()
    assert client.shutdown_requested
    client.worker_alive = False
    client.stopped.emit()
    application.processEvents()
    assert not window.isVisible()
