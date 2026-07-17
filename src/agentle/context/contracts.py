"""Provider-neutral context contribution and assembly contracts."""

from dataclasses import dataclass
from datetime import datetime
from enum import IntEnum, StrEnum

from agentle.foundation import RunId, SessionId, as_utc


class ContributionKind(StrEnum):
    APPLICATION_INSTRUCTIONS = "application_instructions"
    AGENT_INSTRUCTIONS = "agent_instructions"
    HISTORY = "history"
    CURRENT_REQUEST = "current_request"


class ContextPriority(IntEnum):
    APPLICATION = 10
    AGENT = 20
    HISTORY = 30
    REQUEST = 40


class MessageRole(StrEnum):
    USER = "user"
    ASSISTANT = "assistant"


@dataclass(frozen=True, slots=True)
class ContextContribution:
    kind: ContributionKind
    content: str
    source: str
    source_id: str
    priority: ContextPriority
    role: MessageRole | None = None
    occurred_at: datetime | None = None

    def __post_init__(self) -> None:
        if self.occurred_at is not None:
            object.__setattr__(self, "occurred_at", as_utc(self.occurred_at))

    @property
    def provenance_ref(self) -> str:
        return f"{self.source}:{self.source_id}"


@dataclass(frozen=True, slots=True)
class ContextRequest:
    session_id: SessionId
    run_id: RunId
    contributions: tuple[ContextContribution, ...]
    character_limit: int


@dataclass(frozen=True, slots=True)
class AssembledMessage:
    role: MessageRole
    content: str
    provenance_refs: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ProvenanceRecord:
    reference: str
    kind: ContributionKind
    occurred_at: datetime | None


@dataclass(frozen=True, slots=True)
class AssembledContext:
    instructions: tuple[str, ...]
    messages: tuple[AssembledMessage, ...]
    current_request: str
    provenance: tuple[ProvenanceRecord, ...]
    fingerprint: str
