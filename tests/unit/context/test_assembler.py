from datetime import UTC, datetime, timedelta

import pytest

from agentle.context import (
    ContextAssembler,
    ContextContribution,
    ContextPriority,
    ContextRequest,
    ContributionKind,
    MessageRole,
)
from agentle.foundation import AgentleError, RunId, SessionId

NOW = datetime(2026, 1, 1, tzinfo=UTC)


def contribution(
    kind: ContributionKind,
    content: str,
    source_id: str,
    priority: ContextPriority,
    *,
    role: MessageRole | None = None,
    occurred_at: datetime | None = None,
) -> ContextContribution:
    return ContextContribution(
        kind=kind,
        content=content,
        source="test",
        source_id=source_id,
        priority=priority,
        role=role,
        occurred_at=occurred_at,
    )


def request(*items: ContextContribution, limit: int = 10_000) -> ContextRequest:
    return ContextRequest(
        session_id=SessionId("session"),
        run_id=RunId("run"),
        contributions=items,
        character_limit=limit,
    )


def complete_contributions() -> tuple[ContextContribution, ...]:
    return (
        contribution(
            ContributionKind.CURRENT_REQUEST,
            "current",
            "request",
            ContextPriority.REQUEST,
        ),
        contribution(
            ContributionKind.HISTORY,
            "assistant answer",
            "message-2",
            ContextPriority.HISTORY,
            role=MessageRole.ASSISTANT,
            occurred_at=NOW + timedelta(seconds=2),
        ),
        contribution(
            ContributionKind.AGENT_INSTRUCTIONS,
            "agent",
            "agent",
            ContextPriority.AGENT,
        ),
        contribution(
            ContributionKind.HISTORY,
            "user question",
            "message-1",
            ContextPriority.HISTORY,
            role=MessageRole.USER,
            occurred_at=NOW + timedelta(seconds=1),
        ),
        contribution(
            ContributionKind.APPLICATION_INSTRUCTIONS,
            "application",
            "application",
            ContextPriority.APPLICATION,
        ),
    )


def test_assembly_is_ordered_repeatable_and_preserves_provenance() -> None:
    assembler = ContextAssembler()

    first = assembler.assemble(request(*complete_contributions()))
    second = assembler.assemble(request(*complete_contributions()))

    assert first.instructions == ("application", "agent")
    assert [message.content for message in first.messages] == [
        "user question",
        "assistant answer",
    ]
    assert first.current_request == "current"
    assert first.messages[0].provenance_refs == ("test:message-1",)
    assert first.fingerprint == second.fingerprint


@pytest.mark.parametrize(
    "items,code",
    [
        ((), "context.missing_request"),
        (
            (
                contribution(
                    ContributionKind.CURRENT_REQUEST,
                    " ",
                    "request",
                    ContextPriority.REQUEST,
                ),
            ),
            "context.missing_request",
        ),
        (
            (
                contribution(
                    ContributionKind.CURRENT_REQUEST,
                    "hello",
                    "request",
                    ContextPriority.AGENT,
                ),
            ),
            "context.invalid_order",
        ),
        (
            (
                contribution(
                    ContributionKind.CURRENT_REQUEST,
                    "hello",
                    "request",
                    ContextPriority.REQUEST,
                ),
                contribution(
                    ContributionKind.HISTORY,
                    "history",
                    "message",
                    ContextPriority.HISTORY,
                ),
            ),
            "context.invalid_role",
        ),
    ],
)
def test_invalid_context_is_structured(
    items: tuple[ContextContribution, ...], code: str
) -> None:
    with pytest.raises(AgentleError) as caught:
        ContextAssembler().assemble(request(*items))

    assert caught.value.info.code == code


def test_context_limit_is_enforced_without_truncation() -> None:
    items = complete_contributions()

    with pytest.raises(AgentleError) as caught:
        ContextAssembler().assemble(request(*items, limit=5))

    assert caught.value.info.code == "context.limit_exceeded"
