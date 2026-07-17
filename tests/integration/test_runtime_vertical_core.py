import asyncio
from collections.abc import AsyncIterator
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from agentle.agents import (
    AgentDefinition,
    AgentRunEvent,
    AgentRunInput,
    FinalOutput,
    TextDelta,
)
from agentle.context import ContextAssembler
from agentle.execution import LocalExecutionBackend
from agentle.foundation import (
    AgentleError,
    ErrorCategory,
    ErrorInfo,
    new_event_id,
    new_run_id,
)
from agentle.models import ModelCapabilities, ModelDescriptor
from agentle.persistence import (
    MessageRecord,
    MessageRole,
    RunRecord,
    RunStatus,
    SQLitePersistence,
    new_message_id,
)
from agentle.runtime import (
    CancelRun,
    CommandStatus,
    CreateSession,
    EventKind,
    EventSubscription,
    RuntimeEvent,
    RuntimeService,
    Shutdown,
    SubmitPrompt,
    to_stored_event,
)
from agentle.tools import ReadTextTool, ToolCatalog, ToolInvoker


@dataclass
class ManualClock:
    value: float = 0.0

    def utc_now(self) -> datetime:
        return datetime(2026, 1, 1, tzinfo=UTC)

    def monotonic(self) -> float:
        return self.value


class FakeModelBinding:
    def __init__(self) -> None:
        self._descriptor = ModelDescriptor(
            model_id="default-model",
            display_name="Fake model",
            capabilities=ModelCapabilities(streaming_text=True, function_tools=True),
            runner_family="scripted",
        )
        self.closed = False

    @property
    def descriptor(self) -> ModelDescriptor:
        return self._descriptor

    async def close(self) -> None:
        self.closed = True


class ScriptedRunner:
    runner_family = "scripted"

    def __init__(self, *, blocking: bool = False) -> None:
        self.blocking = blocking
        self.closed = False

    def run(self, run_input: AgentRunInput) -> AsyncIterator[AgentRunEvent]:
        return self._run(run_input)

    async def _run(self, run_input: AgentRunInput) -> AsyncIterator[AgentRunEvent]:
        if self.blocking:
            await run_input.cancellation.wait()
            run_input.cancellation.raise_if_cancelled()
        yield TextDelta("hel")
        yield TextDelta("lo")
        yield FinalOutput("hello")

    async def close(self) -> None:
        self.closed = True


async def make_runtime(
    tmp_path: Path, *, blocking: bool = False
) -> tuple[RuntimeService, ScriptedRunner, FakeModelBinding, LocalExecutionBackend]:
    persistence = await SQLitePersistence.open(tmp_path / "runtime.sqlite3")
    backend = LocalExecutionBackend(tmp_path, clock=ManualClock())
    invoker = ToolInvoker(ToolCatalog([ReadTextTool(backend)]), ["read_text"])
    runner = ScriptedRunner(blocking=blocking)
    model = FakeModelBinding()
    service = RuntimeService(
        persistence=persistence,
        context_assembler=ContextAssembler(),
        runner=runner,
        model=model,
        tool_invoker=invoker,
        agent=AgentDefinition(
            agent_id="default",
            display_name="Default",
            instructions="Be helpful.",
            model_id="default-model",
            allowed_tools=("read_text",),
        ),
        clock=ManualClock(),
        application_instructions="You are Agentle.",
        workspace=str(tmp_path),
        shutdown_callbacks=(backend.close,),
    )
    return service, runner, model, backend


async def next_event_of_kind(
    subscription: EventSubscription, expected: EventKind, *, timeout: float = 1
) -> RuntimeEvent:
    while True:
        event = await asyncio.wait_for(subscription.get(), timeout=timeout)
        if event.kind is expected:
            return event


async def create_session(
    service: RuntimeService,
) -> tuple[EventSubscription, RuntimeEvent]:
    subscription = service.subscribe()
    receipt = await service.submit(CreateSession(title="Test"))
    assert receipt.status is CommandStatus.ACCEPTED
    created = await asyncio.wait_for(subscription.get(), timeout=1)
    assert created.kind is EventKind.SESSION_CREATED
    return subscription, created


async def test_runtime_persists_before_streaming_and_replays_terminal_state(
    tmp_path: Path,
) -> None:
    service, runner, model, _ = await make_runtime(tmp_path)
    subscription, created = await create_session(service)

    receipt = await service.submit(
        SubmitPrompt(
            session_id=created.session_id,
            text="Say hello",
            agent_id="default",
            timeout_seconds=5,
        )
    )
    assert receipt.status is CommandStatus.ACCEPTED
    events = [await asyncio.wait_for(subscription.get(), timeout=1) for _ in range(4)]

    assert [event.kind for event in events] == [
        EventKind.RUN_STARTED,
        EventKind.ASSISTANT_DELTA,
        EventKind.ASSISTANT_DELTA,
        EventKind.RUN_COMPLETED,
    ]
    assert [event.sequence for event in [created, *events]] == [1, 2, 3, 4, 5]
    snapshot = await service.load_session(created.session_id)
    assert [message.content for message in snapshot.messages] == ["Say hello", "hello"]
    shutdown = await service.submit(Shutdown(grace_seconds=1))
    assert shutdown.status is CommandStatus.ACCEPTED
    assert runner.closed
    assert model.closed


async def test_runtime_rejects_concurrent_session_run_and_cancels_active_run(
    tmp_path: Path,
) -> None:
    service, _, _, _ = await make_runtime(tmp_path, blocking=True)
    subscription, created = await create_session(service)
    first = await service.submit(
        SubmitPrompt(
            session_id=created.session_id,
            text="Wait",
            agent_id="default",
            timeout_seconds=5,
        )
    )
    assert first.status is CommandStatus.ACCEPTED
    started = await next_event_of_kind(subscription, EventKind.RUN_STARTED)
    second = await service.submit(
        SubmitPrompt(
            session_id=created.session_id,
            text="Second",
            agent_id="default",
            timeout_seconds=5,
        )
    )
    assert second.status is CommandStatus.REJECTED
    assert second.error is not None
    assert second.error.code == "runtime.session_busy"

    assert started.run_id is not None
    cancelled = await service.submit(CancelRun(run_id=started.run_id))
    assert cancelled.status is CommandStatus.ACCEPTED
    terminal = await next_event_of_kind(subscription, EventKind.RUN_CANCELLED)
    assert terminal.run_id == started.run_id
    await service.submit(Shutdown(grace_seconds=1))


async def test_runtime_timeout_becomes_structured_terminal_failure(tmp_path: Path) -> None:
    service, _, _, _ = await make_runtime(tmp_path, blocking=True)
    subscription, created = await create_session(service)
    receipt = await service.submit(
        SubmitPrompt(
            session_id=created.session_id,
            text="Wait",
            agent_id="default",
            timeout_seconds=0.01,
        )
    )
    assert receipt.status is CommandStatus.ACCEPTED
    terminal = await next_event_of_kind(subscription, EventKind.RUN_FAILED)

    error = terminal.payload["error"]
    assert isinstance(error, dict)
    assert error["category"] == "timeout"
    await service.submit(Shutdown(grace_seconds=1))


async def test_shutdown_cancels_active_run_and_closes_owned_resources(
    tmp_path: Path,
) -> None:
    service, runner, model, _ = await make_runtime(tmp_path, blocking=True)
    subscription, created = await create_session(service)
    receipt = await service.submit(
        SubmitPrompt(
            session_id=created.session_id,
            text="Wait",
            agent_id="default",
            timeout_seconds=5,
        )
    )
    assert receipt.status is CommandStatus.ACCEPTED
    await next_event_of_kind(subscription, EventKind.RUN_STARTED)

    shutdown = await service.submit(Shutdown(grace_seconds=1))
    assert shutdown.status is CommandStatus.ACCEPTED
    terminal = await next_event_of_kind(subscription, EventKind.RUN_CANCELLED)
    assert terminal.kind is EventKind.RUN_CANCELLED
    assert runner.closed
    assert model.closed


async def test_persistence_failure_is_not_published_as_a_delta(tmp_path: Path) -> None:
    service, _, _, _ = await make_runtime(tmp_path)
    subscription, created = await create_session(service)
    persistence = service._persistence
    append_event = persistence.append_event
    failed_once = False

    async def fail_first_append(stored_event):  # type: ignore[no-untyped-def]
        nonlocal failed_once
        if not failed_once:
            failed_once = True
            raise AgentleError(
                ErrorInfo(
                    "persistence.unavailable",
                    ErrorCategory.PERSISTENCE,
                    "Persistence is unavailable.",
                    retryable=True,
                )
            )
        await append_event(stored_event)

    persistence.append_event = fail_first_append  # type: ignore[method-assign]
    receipt = await service.submit(
        SubmitPrompt(
            session_id=created.session_id,
            text="Say hello",
            agent_id="default",
            timeout_seconds=5,
        )
    )
    assert receipt.status is CommandStatus.ACCEPTED
    started = await next_event_of_kind(subscription, EventKind.RUN_STARTED)
    terminal = await next_event_of_kind(subscription, EventKind.RUN_FAILED)
    assert terminal.sequence == started.sequence + 1
    error = terminal.payload["error"]
    assert isinstance(error, dict)
    assert error["category"] == "persistence"
    snapshot = await service.load_session(created.session_id)
    assert EventKind.ASSISTANT_DELTA not in {event.kind for event in snapshot.events}
    await service.submit(Shutdown(grace_seconds=1))


async def test_recovery_terminates_run_interrupted_by_previous_process(
    tmp_path: Path,
) -> None:
    service, _, _, _ = await make_runtime(tmp_path)
    subscription, created = await create_session(service)
    persistence = service._persistence
    run_id = new_run_id()
    now = datetime(2026, 1, 1, tzinfo=UTC)
    started = RuntimeEvent(
        event_id=new_event_id(),
        session_id=created.session_id,
        run_id=run_id,
        sequence=2,
        occurred_at=now,
        kind=EventKind.RUN_STARTED,
        payload={"prompt": "interrupted"},
    )
    await persistence.start_run(
        RunRecord(
            run_id,
            created.session_id,
            "default",
            "default-model",
            RunStatus.STARTED,
            now,
        ),
        MessageRecord(
            new_message_id(),
            created.session_id,
            MessageRole.USER,
            "interrupted",
            now,
            run_id,
        ),
        to_stored_event(started),
    )
    service._sequences.pop(created.session_id)

    assert await service.recover_interrupted_runs() == 1
    terminal = await next_event_of_kind(subscription, EventKind.RUN_FAILED)
    assert terminal.sequence == 3
    error = terminal.payload["error"]
    assert isinstance(error, dict)
    assert error["code"] == "runtime.interrupted"
    stored_run = await persistence.get_run(run_id)
    assert stored_run is not None
    assert stored_run.status is RunStatus.FAILED
    await service.submit(Shutdown(grace_seconds=1))
