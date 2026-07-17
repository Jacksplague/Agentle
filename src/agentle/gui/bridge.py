"""Queued Qt signals over the dedicated Runtime asyncio thread."""

from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot

from agentle.foundation import ErrorInfo, RunId, SessionId
from agentle.runtime import (
    CancelRun,
    CommandReceipt,
    CreateSession,
    RuntimeEvent,
    RuntimeFactory,
    RuntimeThreadClient,
    SessionSnapshot,
    Shutdown,
    SubmitPrompt,
)


class QtRuntimeClient(QObject):
    ready = pyqtSignal()
    receipt_received = pyqtSignal(object)
    event_received = pyqtSignal(object)
    snapshot_received = pyqtSignal(object)
    error_received = pyqtSignal(object)
    stopped = pyqtSignal()

    def __init__(self, factory: RuntimeFactory) -> None:
        super().__init__()
        self._shutdown_pending: float | None = None
        self._worker = RuntimeThreadClient(
            factory,
            on_ready=self._runtime_ready,
            on_receipt=self._emit_receipt,
            on_event=self._emit_event,
            on_snapshot=self._emit_snapshot,
            on_error=self._emit_error,
            on_stopped=self.stopped.emit,
        )

    @property
    def worker_alive(self) -> bool:
        return self._worker.alive

    @pyqtSlot()
    def start(self) -> None:
        self._worker.start()

    def create_session(self, title: str | None = None) -> None:
        self._worker.submit(CreateSession(title=title))

    def submit_prompt(
        self,
        session_id: SessionId,
        text: str,
        *,
        agent_id: str = "default",
        timeout_seconds: float = 120,
    ) -> None:
        self._worker.submit(
            SubmitPrompt(
                session_id=session_id,
                text=text,
                agent_id=agent_id,
                timeout_seconds=timeout_seconds,
            )
        )

    def cancel_run(self, run_id: RunId) -> None:
        self._worker.submit(CancelRun(run_id=run_id))

    def load_session(self, session_id: SessionId) -> None:
        self._worker.load_session(session_id)

    def shutdown(self, grace_seconds: float = 5) -> None:
        try:
            self._worker.submit(Shutdown(grace_seconds=grace_seconds))
        except RuntimeError:
            self._shutdown_pending = grace_seconds

    def join(self, timeout: float | None = None) -> bool:
        return self._worker.join(timeout)

    def _emit_receipt(self, receipt: CommandReceipt) -> None:
        self.receipt_received.emit(receipt)
        if receipt.error is not None:
            self.error_received.emit(receipt.error)

    def _runtime_ready(self) -> None:
        grace_seconds = self._shutdown_pending
        self._shutdown_pending = None
        if grace_seconds is not None:
            self._worker.submit(Shutdown(grace_seconds=grace_seconds))
        else:
            self.ready.emit()

    def _emit_event(self, event: RuntimeEvent) -> None:
        self.event_received.emit(event)

    def _emit_snapshot(self, snapshot: SessionSnapshot) -> None:
        self.snapshot_received.emit(snapshot)

    def _emit_error(self, error: ErrorInfo) -> None:
        self.error_received.emit(error)
