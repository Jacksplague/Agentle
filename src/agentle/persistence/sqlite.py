"""SQLite implementation of the explicit persistence contracts."""

import asyncio
import json
import sqlite3
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
from typing import cast

from agentle.foundation import (
    AgentleError,
    ErrorCategory,
    ErrorDetail,
    ErrorInfo,
    EventId,
    RunId,
    SessionId,
)

from .contracts import (
    MessageId,
    MessageRecord,
    MessageRole,
    RunRecord,
    RunStatus,
    SessionRecord,
    StoredRuntimeEvent,
)

SCHEMA_VERSION = 1


def _persistence_error(
    code: str,
    message: str,
    *,
    details: dict[str, ErrorDetail] | None = None,
    retryable: bool = False,
) -> AgentleError:
    return AgentleError(
        ErrorInfo(
            code=code,
            category=ErrorCategory.PERSISTENCE,
            message=message,
            details={} if details is None else details,
            retryable=retryable,
        )
    )


def _timestamp(value: datetime) -> str:
    return value.isoformat()


def _parse_timestamp(value: object) -> datetime:
    if not isinstance(value, str):
        raise _persistence_error("persistence.corrupt", "A stored timestamp is invalid.")
    try:
        return datetime.fromisoformat(value)
    except ValueError as error:
        raise _persistence_error("persistence.corrupt", "A stored timestamp is invalid.") from error


def _error_json(error: ErrorInfo | None) -> str | None:
    if error is None:
        return None
    return json.dumps(error.to_dict(), ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _parse_error(value: object) -> ErrorInfo | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise _persistence_error("persistence.corrupt", "A stored error is invalid.")
    try:
        raw = cast(dict[str, object], json.loads(value))
        details = cast(dict[str, ErrorDetail], raw.get("details", {}))
        cause_code_value = raw.get("cause_code")
        cause_code = cast(str | None, cause_code_value)
        return ErrorInfo(
            code=cast(str, raw["code"]),
            category=ErrorCategory(cast(str, raw["category"])),
            message=cast(str, raw["message"]),
            retryable=cast(bool, raw["retryable"]),
            details=details,
            cause_code=cause_code,
        )
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
        raise _persistence_error("persistence.corrupt", "A stored error is invalid.") from error


class SQLitePersistence:
    """One SQLite connection owned by one dedicated worker thread."""

    def __init__(self, path: Path, busy_timeout_ms: int) -> None:
        self._path = path
        self._busy_timeout_ms = busy_timeout_ms
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="agentle-sqlite")
        self._connection: sqlite3.Connection | None = None
        self._closed = False

    @classmethod
    async def open(
        cls, path: str | Path, *, busy_timeout_ms: int = 5_000
    ) -> "SQLitePersistence":
        if busy_timeout_ms < 0:
            raise ValueError("busy timeout cannot be negative")
        persistence = cls(Path(path), busy_timeout_ms)
        await persistence._call(persistence._initialize_sync)
        return persistence

    async def _call[T](self, operation: Callable[[], T]) -> T:
        if self._closed:
            raise _persistence_error(
                "persistence.unavailable", "Persistence is already closed."
            )
        loop = asyncio.get_running_loop()
        try:
            return await loop.run_in_executor(self._executor, operation)
        except AgentleError:
            raise
        except sqlite3.IntegrityError as error:
            raise _persistence_error(
                "persistence.constraint", "A persistence constraint was violated."
            ) from error
        except sqlite3.DatabaseError as error:
            raise _persistence_error(
                "persistence.transaction",
                "The persistence transaction failed.",
                retryable=True,
            ) from error

    def _initialize_sync(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self._path)
        self._connection = connection
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute(f"PRAGMA busy_timeout = {self._busy_timeout_ms}")
        try:
            connection.execute("PRAGMA journal_mode = WAL")
        except sqlite3.DatabaseError:
            connection.execute("PRAGMA journal_mode = DELETE")
        connection.execute("CREATE TABLE IF NOT EXISTS schema_meta (version INTEGER NOT NULL)")
        version_row = connection.execute("SELECT version FROM schema_meta LIMIT 1").fetchone()
        if version_row is None:
            connection.execute("INSERT INTO schema_meta(version) VALUES (?)", (SCHEMA_VERSION,))
        else:
            version = cast(int, version_row[0])
            if version > SCHEMA_VERSION:
                raise _persistence_error(
                    "persistence.schema_newer",
                    "The database schema is newer than this Agentle version supports.",
                    details={"database_version": version, "supported_version": SCHEMA_VERSION},
                )
            if version < SCHEMA_VERSION:
                raise _persistence_error(
                    "persistence.corrupt", "The database schema requires a missing migration."
                )
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY,
                title TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS runs (
                id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL REFERENCES sessions(id),
                agent_id TEXT NOT NULL,
                model_id TEXT NOT NULL,
                status TEXT NOT NULL,
                started_at TEXT NOT NULL,
                finished_at TEXT,
                error_json TEXT
            );
            CREATE TABLE IF NOT EXISTS messages (
                id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL REFERENCES sessions(id),
                run_id TEXT REFERENCES runs(id),
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS events (
                event_id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL REFERENCES sessions(id),
                run_id TEXT REFERENCES runs(id),
                sequence INTEGER NOT NULL,
                occurred_at TEXT NOT NULL,
                kind TEXT NOT NULL,
                schema_version INTEGER NOT NULL,
                payload_json TEXT NOT NULL,
                UNIQUE(session_id, sequence)
            );
            """
        )
        connection.commit()

    def _conn(self) -> sqlite3.Connection:
        if self._connection is None:
            raise _persistence_error("persistence.unavailable", "Persistence is not initialized.")
        return self._connection

    @staticmethod
    def _validate_event(
        event: StoredRuntimeEvent, session_id: SessionId, run_id: RunId | None
    ) -> None:
        if event.session_id != session_id or event.run_id != run_id:
            raise _persistence_error(
                "persistence.constraint", "The event correlation identifiers do not match."
            )

    @staticmethod
    def _insert_event(connection: sqlite3.Connection, event: StoredRuntimeEvent) -> None:
        row = connection.execute(
            "SELECT COALESCE(MAX(sequence), 0) FROM events WHERE session_id = ?",
            (event.session_id,),
        ).fetchone()
        previous = 0 if row is None else cast(int, row[0])
        expected = previous + 1
        if event.sequence != expected:
            raise _persistence_error(
                "persistence.event_order",
                "The runtime event sequence is out of order.",
                details={"expected": expected, "actual": event.sequence},
            )
        connection.execute(
            """
            INSERT INTO events(
                event_id, session_id, run_id, sequence, occurred_at, kind,
                schema_version, payload_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                event.event_id,
                event.session_id,
                event.run_id,
                event.sequence,
                _timestamp(event.occurred_at),
                event.kind,
                event.schema_version,
                event.payload_json,
            ),
        )

    async def create_session(
        self, session: SessionRecord, created_event: StoredRuntimeEvent
    ) -> None:
        def operation() -> None:
            self._validate_event(created_event, session.session_id, None)
            connection = self._conn()
            with connection:
                connection.execute(
                    "INSERT INTO sessions(id, title, created_at, updated_at) VALUES (?, ?, ?, ?)",
                    (
                        session.session_id,
                        session.title,
                        _timestamp(session.created_at),
                        _timestamp(session.updated_at),
                    ),
                )
                self._insert_event(connection, created_event)

        await self._call(operation)

    async def get_session(self, session_id: SessionId) -> SessionRecord | None:
        def operation() -> SessionRecord | None:
            row = self._conn().execute(
                "SELECT id, title, created_at, updated_at FROM sessions WHERE id = ?",
                (session_id,),
            ).fetchone()
            if row is None:
                return None
            return SessionRecord(
                session_id=SessionId(cast(str, row[0])),
                title=cast(str | None, row[1]),
                created_at=_parse_timestamp(row[2]),
                updated_at=_parse_timestamp(row[3]),
            )

        return await self._call(operation)

    async def list_messages(self, session_id: SessionId) -> list[MessageRecord]:
        def operation() -> list[MessageRecord]:
            rows = self._conn().execute(
                """
                SELECT id, session_id, run_id, role, content, created_at
                FROM messages WHERE session_id = ? ORDER BY rowid
                """,
                (session_id,),
            ).fetchall()
            return [self._message_from_row(row) for row in rows]

        return await self._call(operation)

    @staticmethod
    def _message_from_row(row: tuple[object, ...]) -> MessageRecord:
        run_value = cast(str | None, row[2])
        return MessageRecord(
            message_id=MessageId(cast(str, row[0])),
            session_id=SessionId(cast(str, row[1])),
            run_id=None if run_value is None else RunId(run_value),
            role=MessageRole(cast(str, row[3])),
            content=cast(str, row[4]),
            created_at=_parse_timestamp(row[5]),
        )

    async def start_run(
        self,
        run: RunRecord,
        user_message: MessageRecord,
        started_event: StoredRuntimeEvent,
    ) -> None:
        def operation() -> None:
            if run.status is not RunStatus.STARTED:
                raise _persistence_error(
                    "persistence.constraint", "A new run must have started status."
                )
            if (
                user_message.session_id != run.session_id
                or user_message.run_id != run.run_id
                or user_message.role is not MessageRole.USER
            ):
                raise _persistence_error(
                    "persistence.constraint", "The starting user message does not match the run."
                )
            self._validate_event(started_event, run.session_id, run.run_id)
            connection = self._conn()
            with connection:
                connection.execute(
                    """
                    INSERT INTO runs(
                        id, session_id, agent_id, model_id, status, started_at,
                        finished_at, error_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        run.run_id,
                        run.session_id,
                        run.agent_id,
                        run.model_id,
                        run.status.value,
                        _timestamp(run.started_at),
                        None,
                        None,
                    ),
                )
                self._insert_message(connection, user_message)
                self._insert_event(connection, started_event)
                self._touch_session(connection, run.session_id, started_event.occurred_at)

        await self._call(operation)

    @staticmethod
    def _insert_message(connection: sqlite3.Connection, message: MessageRecord) -> None:
        connection.execute(
            """
            INSERT INTO messages(id, session_id, run_id, role, content, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                message.message_id,
                message.session_id,
                message.run_id,
                message.role.value,
                message.content,
                _timestamp(message.created_at),
            ),
        )

    @staticmethod
    def _touch_session(
        connection: sqlite3.Connection, session_id: SessionId, occurred_at: datetime
    ) -> None:
        connection.execute(
            "UPDATE sessions SET updated_at = ? WHERE id = ?",
            (_timestamp(occurred_at), session_id),
        )

    async def append_event(self, event: StoredRuntimeEvent) -> None:
        def operation() -> None:
            connection = self._conn()
            with connection:
                self._insert_event(connection, event)
                self._touch_session(connection, event.session_id, event.occurred_at)

        await self._call(operation)

    async def complete_run(
        self,
        run_id: RunId,
        assistant_message: MessageRecord,
        terminal_event: StoredRuntimeEvent,
    ) -> None:
        def operation() -> None:
            run = self._require_started_run(run_id)
            if (
                assistant_message.session_id != run.session_id
                or assistant_message.run_id != run_id
                or assistant_message.role is not MessageRole.ASSISTANT
            ):
                raise _persistence_error(
                    "persistence.constraint", "The assistant message does not match the run."
                )
            self._validate_event(terminal_event, run.session_id, run_id)
            connection = self._conn()
            with connection:
                self._insert_message(connection, assistant_message)
                connection.execute(
                    """
                    UPDATE runs SET status = ?, finished_at = ?, error_json = NULL WHERE id = ?
                    """,
                    (RunStatus.COMPLETED.value, _timestamp(terminal_event.occurred_at), run_id),
                )
                self._insert_event(connection, terminal_event)
                self._touch_session(connection, run.session_id, terminal_event.occurred_at)

        await self._call(operation)

    async def terminate_run(
        self,
        run_id: RunId,
        status: RunStatus,
        terminal_event: StoredRuntimeEvent,
        error: ErrorInfo | None,
    ) -> None:
        if status not in {RunStatus.FAILED, RunStatus.CANCELLED}:
            raise ValueError("terminated runs must be failed or cancelled")

        def operation() -> None:
            run = self._require_started_run(run_id)
            self._validate_event(terminal_event, run.session_id, run_id)
            connection = self._conn()
            with connection:
                connection.execute(
                    "UPDATE runs SET status = ?, finished_at = ?, error_json = ? WHERE id = ?",
                    (
                        status.value,
                        _timestamp(terminal_event.occurred_at),
                        _error_json(error),
                        run_id,
                    ),
                )
                self._insert_event(connection, terminal_event)
                self._touch_session(connection, run.session_id, terminal_event.occurred_at)

        await self._call(operation)

    def _require_started_run(self, run_id: RunId) -> RunRecord:
        run = self._get_run_sync(run_id)
        if run is None or run.status is not RunStatus.STARTED:
            raise _persistence_error(
                "persistence.constraint", "The run does not exist or is already terminal."
            )
        return run

    async def get_run(self, run_id: RunId) -> RunRecord | None:
        return await self._call(lambda: self._get_run_sync(run_id))

    def _get_run_sync(self, run_id: RunId) -> RunRecord | None:
        row = self._conn().execute(
            """
            SELECT id, session_id, agent_id, model_id, status, started_at,
                   finished_at, error_json
            FROM runs WHERE id = ?
            """,
            (run_id,),
        ).fetchone()
        return None if row is None else self._run_from_row(row)

    @staticmethod
    def _run_from_row(row: tuple[object, ...]) -> RunRecord:
        finished = row[6]
        return RunRecord(
            run_id=RunId(cast(str, row[0])),
            session_id=SessionId(cast(str, row[1])),
            agent_id=cast(str, row[2]),
            model_id=cast(str, row[3]),
            status=RunStatus(cast(str, row[4])),
            started_at=_parse_timestamp(row[5]),
            finished_at=None if finished is None else _parse_timestamp(finished),
            error=_parse_error(row[7]),
        )

    async def list_events(
        self, session_id: SessionId, after_sequence: int = 0
    ) -> list[StoredRuntimeEvent]:
        def operation() -> list[StoredRuntimeEvent]:
            rows = self._conn().execute(
                """
                SELECT event_id, session_id, run_id, sequence, occurred_at, kind,
                       schema_version, payload_json
                FROM events WHERE session_id = ? AND sequence > ? ORDER BY sequence
                """,
                (session_id, after_sequence),
            ).fetchall()
            return [self._event_from_row(row) for row in rows]

        return await self._call(operation)

    @staticmethod
    def _event_from_row(row: tuple[object, ...]) -> StoredRuntimeEvent:
        run_value = cast(str | None, row[2])
        return StoredRuntimeEvent(
            event_id=EventId(cast(str, row[0])),
            session_id=SessionId(cast(str, row[1])),
            run_id=None if run_value is None else RunId(run_value),
            sequence=cast(int, row[3]),
            occurred_at=_parse_timestamp(row[4]),
            kind=cast(str, row[5]),
            schema_version=cast(int, row[6]),
            payload_json=cast(str, row[7]),
        )

    async def last_sequence(self, session_id: SessionId) -> int:
        def operation() -> int:
            row = self._conn().execute(
                "SELECT COALESCE(MAX(sequence), 0) FROM events WHERE session_id = ?",
                (session_id,),
            ).fetchone()
            return 0 if row is None else cast(int, row[0])

        return await self._call(operation)

    async def list_incomplete_runs(self) -> list[RunRecord]:
        def operation() -> list[RunRecord]:
            rows = self._conn().execute(
                """
                SELECT id, session_id, agent_id, model_id, status, started_at,
                       finished_at, error_json
                FROM runs WHERE status = ? ORDER BY rowid
                """,
                (RunStatus.STARTED.value,),
            ).fetchall()
            return [self._run_from_row(row) for row in rows]

        return await self._call(operation)

    async def close(self) -> None:
        if self._closed:
            return

        def operation() -> None:
            if self._connection is not None:
                self._connection.close()
                self._connection = None

        await self._call(operation)
        self._closed = True
        await asyncio.to_thread(self._executor.shutdown, wait=True, cancel_futures=True)
