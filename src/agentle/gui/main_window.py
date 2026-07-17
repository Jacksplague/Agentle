"""Minimal Phase 1 desktop window driven only by Runtime contracts."""

from PyQt6.QtCore import QTimer
from PyQt6.QtGui import QCloseEvent
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QListWidget,
    QMainWindow,
    QPlainTextEdit,
    QPushButton,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from agentle.foundation import ErrorInfo
from agentle.runtime import RuntimeEvent

from .bridge import QtRuntimeClient
from .state import SessionViewState, ViewStatus, reduce_event


class MainWindow(QMainWindow):
    def __init__(self, runtime_client: QtRuntimeClient) -> None:
        super().__init__()
        self._runtime = runtime_client
        self._state = SessionViewState()
        self._shutdown_complete = False
        self.setWindowTitle("Agentle")
        self.resize(840, 680)

        self.transcript = QTextBrowser()
        self.transcript.setObjectName("transcript")
        self.activity = QListWidget()
        self.activity.setObjectName("activity")
        self.activity.setMaximumHeight(130)
        self.prompt = QPlainTextEdit()
        self.prompt.setObjectName("prompt")
        self.prompt.setPlaceholderText("Ask Agentle…")
        self.prompt.setMaximumHeight(120)
        self.send_button = QPushButton("Send")
        self.send_button.setObjectName("send")
        self.stop_button = QPushButton("Stop")
        self.stop_button.setObjectName("stop")
        self.status_label = QLabel("Starting runtime…")
        self.status_label.setObjectName("status")
        self.error_label = QLabel("")
        self.error_label.setObjectName("error")
        self.error_label.setWordWrap(True)

        buttons = QHBoxLayout()
        buttons.addWidget(self.send_button)
        buttons.addWidget(self.stop_button)
        layout = QVBoxLayout()
        layout.addWidget(self.transcript, 1)
        layout.addWidget(QLabel("Activity"))
        layout.addWidget(self.activity)
        layout.addWidget(self.prompt)
        layout.addLayout(buttons)
        layout.addWidget(self.status_label)
        layout.addWidget(self.error_label)
        central = QWidget()
        central.setLayout(layout)
        self.setCentralWidget(central)

        self.send_button.clicked.connect(self._send)
        self.stop_button.clicked.connect(self._stop)
        self._runtime.ready.connect(self._runtime_ready)
        self._runtime.event_received.connect(self._event_received)
        self._runtime.error_received.connect(self._error_received)
        self._runtime.stopped.connect(self._runtime_stopped)
        self._render()

    def start(self) -> None:
        self._runtime.start()

    def _runtime_ready(self) -> None:
        self._runtime.create_session("Agentle session")

    def _send(self) -> None:
        text = self.prompt.toPlainText().strip()
        if not text or self._state.session_id is None:
            return
        self._runtime.submit_prompt(self._state.session_id, text)
        self.prompt.clear()

    def _stop(self) -> None:
        run_id = self._state.active_run_id
        if run_id is None:
            return
        self._state = SessionViewState(
            session_id=self._state.session_id,
            last_sequence=self._state.last_sequence,
            transcript=self._state.transcript,
            activity=self._state.activity,
            active_run_id=self._state.active_run_id,
            status=ViewStatus.CANCELLING,
            error=self._state.error,
        )
        self._runtime.cancel_run(run_id)
        self._render()

    def _event_received(self, value: object) -> None:
        if not isinstance(value, RuntimeEvent):
            return
        self._state = reduce_event(self._state, value)
        self._render()

    def _error_received(self, value: object) -> None:
        if not isinstance(value, ErrorInfo):
            return
        self.error_label.setText(f"{value.message} ({value.code})")

    def _runtime_stopped(self) -> None:
        self._shutdown_complete = True
        if self._state.status is ViewStatus.CLOSING:
            self.close()
        else:
            self._state = SessionViewState(
                session_id=self._state.session_id,
                last_sequence=self._state.last_sequence,
                transcript=self._state.transcript,
                activity=self._state.activity,
                active_run_id=None,
                status=ViewStatus.FAILED,
                error=self._state.error,
            )
            self._render()

    def _render(self) -> None:
        transcript = "\n\n".join(
            f"{item.role.title()}: {item.content}" for item in self._state.transcript
        )
        self.transcript.setPlainText(transcript)
        self.activity.clear()
        self.activity.addItems([item.text for item in self._state.activity])
        self.status_label.setText(self._state.status.value.title())
        if self._state.error is not None:
            self.error_label.setText(
                f"{self._state.error.message} ({self._state.error.code})"
            )
        active = self._state.active_run_id is not None
        closing = self._state.status is ViewStatus.CLOSING
        self.send_button.setEnabled(
            self._state.status in {ViewStatus.IDLE, ViewStatus.FAILED}
            and self._state.session_id is not None
            and not closing
        )
        self.stop_button.setEnabled(active and not closing)
        self.prompt.setEnabled(not active and not closing)

    def closeEvent(self, event: QCloseEvent | None) -> None:
        if event is None:
            return
        if self._shutdown_complete or not self._runtime.worker_alive:
            event.accept()
            return
        event.ignore()
        if self._state.status is not ViewStatus.CLOSING:
            self._state = SessionViewState(
                session_id=self._state.session_id,
                last_sequence=self._state.last_sequence,
                transcript=self._state.transcript,
                activity=self._state.activity,
                active_run_id=self._state.active_run_id,
                status=ViewStatus.CLOSING,
                error=self._state.error,
            )
            self._render()
            QTimer.singleShot(0, self._runtime.shutdown)
