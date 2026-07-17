"""Explicit persistence records, protocols, and adapters."""

from .contracts import (
    MessageId,
    MessageRecord,
    MessageRole,
    Persistence,
    RunJournal,
    RunRecord,
    RunStatus,
    SessionRecord,
    SessionRepository,
    StoredRuntimeEvent,
    new_message_id,
)
from .sqlite import SCHEMA_VERSION, SQLitePersistence

__all__ = [
    "SCHEMA_VERSION",
    "MessageId",
    "MessageRecord",
    "MessageRole",
    "Persistence",
    "RunJournal",
    "RunRecord",
    "RunStatus",
    "SQLitePersistence",
    "SessionRecord",
    "SessionRepository",
    "StoredRuntimeEvent",
    "new_message_id",
]
