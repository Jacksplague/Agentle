"""Phase 1 runtime command handling and run supervision."""

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from agentle.agents import (
    AgentDefinition,
    AgentRunEvent,
    AgentRunInput,
    AgentRunner,
    FinalOutput,
    TextDelta,
    ToolCompleted,
    ToolFailed,
    ToolRequested,
    ToolStarted,
    UsageUpdated,
)
from agentle.context import (
    AssembledContext,
    ContextAssembler,
    ContextContribution,
    ContextPriority,
    ContextRequest,
    ContributionKind,
)
from agentle.context import (
    MessageRole as ContextMessageRole,
)
from agentle.foundation import (
    AgentleError,
    CancellationSource,
    Clock,
    Deadline,
    ErrorCategory,
    ErrorInfo,
    RunId,
    SessionId,
    error_info_from_exception,
    new_event_id,
    new_run_id,
    new_session_id,
)
from agentle.models import ModelBinding
from agentle.persistence import (
    MessageRecord,
    MessageRole,
    Persistence,
    RunRecord,
    RunStatus,
    SessionRecord,
    new_message_id,
)
from agentle.tools import ToolInvoker

from .commands import (
    CancelRun,
    CommandReceipt,
    CommandStatus,
    CreateSession,
    RuntimeCommand,
    Shutdown,
    SubmitPrompt,
)
from .events import EventKind, JsonValue, RuntimeEvent
from .publisher import EventPublisher, EventSubscription
from .storage import from_stored_event, to_stored_event


def _runtime_error(code: str, message: str) -> AgentleError:
    return AgentleError(ErrorInfo(code=code, category=ErrorCategory.INTERNAL, message=message))


def _error_payload(error: ErrorInfo) -> dict[str, JsonValue]:
    return {
        "code": error.code,
        "category": error.category.value,
        "message": error.message,
        "retryable": error.retryable,
        "details": dict(error.details),
        "cause_code": error.cause_code,
    }


@dataclass(frozen=True, slots=True)
class SessionSnapshot:
    session: SessionRecord
    messages: tuple[MessageRecord, ...]
    events: tuple[RuntimeEvent, ...]


@dataclass(slots=True)
class _RunState:
    session_id: SessionId
    run_id: RunId
    cancellation: CancellationSource
    task: asyncio.Task[None]


class RuntimeService:
    def __init__(
        self,
        *,
        persistence: Persistence,
        context_assembler: ContextAssembler,
        runner: AgentRunner,
        model: ModelBinding,
        tool_invoker: ToolInvoker,
        agent: AgentDefinition,
        clock: Clock,
        application_instructions: str,
        workspace: str,
        context_character_limit: int = 100_000,
        publisher: EventPublisher | None = None,
        shutdown_callbacks: tuple[Callable[[float], Awaitable[None]], ...] = (),
    ) -> None:
        if runner.runner_family != model.descriptor.runner_family:
            raise AgentleError(
                ErrorInfo(
                    code="agent.model_incompatible",
                    category=ErrorCategory.CONFIGURATION,
                    message="The configured agent runner and model binding are incompatible.",
                )
            )
        if agent.model_id != model.descriptor.model_id:
            raise ValueError("agent and model identifiers do not match")
        configured_tools = tuple(definition.name for definition in tool_invoker.definitions)
        if configured_tools != agent.allowed_tools:
            raise ValueError("agent and tool invoker allow-lists do not match")
        self._persistence = persistence
        self._context_assembler = context_assembler
        self._runner = runner
        self._model = model
        self._tool_invoker = tool_invoker
        self._agent = agent
        self._clock = clock
        self._application_instructions = application_instructions
        self._workspace = workspace
        self._context_character_limit = context_character_limit
        self._publisher = EventPublisher() if publisher is None else publisher
        self._shutdown_callbacks = shutdown_callbacks
        self._sequences: dict[SessionId, int] = {}
        self._active_by_session: dict[SessionId, _RunState] = {}
        self._active_by_run: dict[RunId, _RunState] = {}
        self._tasks: set[asyncio.Task[None]] = set()
        self._accepting = True
        self._closed = False

    def subscribe(self) -> EventSubscription:
        return self._publisher.subscribe()

    async def recover_interrupted_runs(self) -> int:
        """Terminate runs left nonterminal by a prior process interruption."""

        recovered = 0
        for run in await self._persistence.list_incomplete_runs():
            await self._seed_sequence(run.session_id)
            error = ErrorInfo(
                code="runtime.interrupted",
                category=ErrorCategory.INTERNAL,
                message="The run was interrupted before the previous shutdown completed.",
                retryable=True,
            )
            terminal = self._new_event(
                run.session_id,
                EventKind.RUN_FAILED,
                {"error": _error_payload(error)},
                run_id=run.run_id,
            )
            await self._persistence.terminate_run(
                run.run_id,
                RunStatus.FAILED,
                to_stored_event(terminal),
                error,
            )
            self._mark_event_committed(terminal)
            self._publisher.publish(terminal)
            recovered += 1
        return recovered

    async def load_session(self, session_id: SessionId) -> SessionSnapshot:
        session = await self._persistence.get_session(session_id)
        if session is None:
            raise _runtime_error(
                "runtime.session_not_found", "The requested session does not exist."
            )
        messages = await self._persistence.list_messages(session_id)
        stored_events = await self._persistence.list_events(session_id)
        if stored_events:
            self._sequences[session_id] = stored_events[-1].sequence
        return SessionSnapshot(
            session=session,
            messages=tuple(messages),
            events=tuple(from_stored_event(event) for event in stored_events),
        )

    async def submit(self, command: RuntimeCommand) -> CommandReceipt:
        if not self._accepting and not isinstance(command, Shutdown):
            return self._rejected(
                command,
                ErrorInfo(
                    code="runtime.shutting_down",
                    category=ErrorCategory.INTERNAL,
                    message="The runtime is shutting down and cannot accept new commands.",
                ),
            )
        try:
            if isinstance(command, CreateSession):
                await self._create_session(command)
            elif isinstance(command, SubmitPrompt):
                await self._submit_prompt(command)
            elif isinstance(command, CancelRun):
                self._cancel_run(command)
            elif isinstance(command, Shutdown):
                await self._shutdown(command.grace_seconds)
            else:
                raise _runtime_error("runtime.unknown_command", "The command is not supported.")
        except BaseException as error:
            if isinstance(error, (KeyboardInterrupt, SystemExit)):
                raise
            return self._rejected(command, error_info_from_exception(error))
        return CommandReceipt(command_id=command.command_id, status=CommandStatus.ACCEPTED)

    @staticmethod
    def _rejected(command: RuntimeCommand, error: ErrorInfo) -> CommandReceipt:
        return CommandReceipt(
            command_id=command.command_id,
            status=CommandStatus.REJECTED,
            error=error,
        )

    async def _create_session(self, command: CreateSession) -> None:
        session_id = new_session_id()
        now = self._clock.utc_now()
        session = SessionRecord(
            session_id=session_id,
            title=command.title,
            created_at=now,
            updated_at=now,
        )
        event = RuntimeEvent(
            event_id=new_event_id(),
            session_id=session_id,
            sequence=1,
            occurred_at=now,
            kind=EventKind.SESSION_CREATED,
            payload={"title": command.title},
        )
        await self._persistence.create_session(session, to_stored_event(event))
        self._sequences[session_id] = 1
        self._publisher.publish(event)

    async def _submit_prompt(self, command: SubmitPrompt) -> None:
        session = await self._persistence.get_session(command.session_id)
        if session is None:
            raise _runtime_error(
                "runtime.session_not_found", "The requested session does not exist."
            )
        if command.session_id in self._active_by_session:
            raise _runtime_error("runtime.session_busy", "The session already has an active run.")
        if command.agent_id != self._agent.agent_id:
            raise _runtime_error(
                "runtime.agent_not_found", "The requested agent is not configured."
            )
        history = tuple(await self._persistence.list_messages(command.session_id))
        await self._seed_sequence(command.session_id)
        run_id = new_run_id()
        now = self._clock.utc_now()
        started_event = self._new_event(
            command.session_id,
            EventKind.RUN_STARTED,
            {
                "agent_id": self._agent.agent_id,
                "model_id": self._model.descriptor.model_id,
                "prompt": command.text,
            },
            run_id=run_id,
        )
        run = RunRecord(
            run_id=run_id,
            session_id=command.session_id,
            agent_id=self._agent.agent_id,
            model_id=self._model.descriptor.model_id,
            status=RunStatus.STARTED,
            started_at=now,
        )
        user_message = MessageRecord(
            message_id=new_message_id(),
            session_id=command.session_id,
            run_id=run_id,
            role=MessageRole.USER,
            content=command.text,
            created_at=now,
        )
        await self._persistence.start_run(run, user_message, to_stored_event(started_event))
        self._mark_event_committed(started_event)
        self._publisher.publish(started_event)
        cancellation = CancellationSource()
        deadline = Deadline.after(command.timeout_seconds, self._clock)
        task = asyncio.create_task(
            self._execute_run(run, user_message, history, deadline, cancellation),
            name=f"agentle-run-{run_id}",
        )
        state = _RunState(command.session_id, run_id, cancellation, task)
        self._active_by_session[command.session_id] = state
        self._active_by_run[run_id] = state
        self._tasks.add(task)
        task.add_done_callback(self._task_done)
        # Ensure the task enters its supervision boundary before a caller can
        # immediately submit cancellation or shutdown.
        await asyncio.sleep(0)

    def _cancel_run(self, command: CancelRun) -> None:
        state = self._active_by_run.get(command.run_id)
        if state is None:
            raise _runtime_error("runtime.run_not_found", "The requested run is not active.")
        state.cancellation.cancel()
        state.task.cancel()

    async def _execute_run(
        self,
        run: RunRecord,
        user_message: MessageRecord,
        history: tuple[MessageRecord, ...],
        deadline: Deadline,
        cancellation: CancellationSource,
    ) -> None:
        try:
            context = self._assemble_context(run, user_message, history)
            run_input = AgentRunInput(
                session_id=run.session_id,
                run_id=run.run_id,
                definition=self._agent,
                context=context,
                model=self._model,
                tool_invoker=self._tool_invoker,
                workspace=self._workspace,
                deadline=deadline,
                cancellation=cancellation.token,
            )
            final_output: str | None = None
            async with asyncio.timeout(deadline.remaining(self._clock)):
                async for runner_event in self._runner.run(run_input):
                    cancellation.token.raise_if_cancelled()
                    if isinstance(runner_event, FinalOutput):
                        if final_output is not None:
                            raise _runtime_error(
                                "agent.invalid_output", "The runner emitted multiple final outputs."
                            )
                        final_output = runner_event.output
                    else:
                        await self._record_runner_event(run, runner_event)
            if final_output is None:
                raise _runtime_error(
                    "agent.incomplete_stream", "The runner ended without a final output."
                )
            terminal = self._new_event(
                run.session_id,
                EventKind.RUN_COMPLETED,
                {"output": final_output},
                run_id=run.run_id,
            )
            assistant_message = MessageRecord(
                message_id=new_message_id(),
                session_id=run.session_id,
                run_id=run.run_id,
                role=MessageRole.ASSISTANT,
                content=final_output,
                created_at=terminal.occurred_at,
            )
            await self._persistence.complete_run(
                run.run_id, assistant_message, to_stored_event(terminal)
            )
            self._mark_event_committed(terminal)
            self._publisher.publish(terminal)
        except asyncio.CancelledError as error:
            await self._record_terminal_failure(
                run, EventKind.RUN_CANCELLED, RunStatus.CANCELLED, error_info_from_exception(error)
            )
        except Exception as error:
            await self._record_terminal_failure(
                run, EventKind.RUN_FAILED, RunStatus.FAILED, error_info_from_exception(error)
            )
        finally:
            self._active_by_session.pop(run.session_id, None)
            self._active_by_run.pop(run.run_id, None)

    def _assemble_context(
        self,
        run: RunRecord,
        user_message: MessageRecord,
        history: tuple[MessageRecord, ...],
    ) -> AssembledContext:
        contributions: list[ContextContribution] = []
        if self._application_instructions:
            contributions.append(
                ContextContribution(
                    kind=ContributionKind.APPLICATION_INSTRUCTIONS,
                    content=self._application_instructions,
                    source="application",
                    source_id="phase-1",
                    priority=ContextPriority.APPLICATION,
                )
            )
        contributions.append(
            ContextContribution(
                kind=ContributionKind.AGENT_INSTRUCTIONS,
                content=self._agent.instructions,
                source="agent",
                source_id=self._agent.agent_id,
                priority=ContextPriority.AGENT,
            )
        )
        for message in history:
            contributions.append(
                ContextContribution(
                    kind=ContributionKind.HISTORY,
                    content=message.content,
                    source="message",
                    source_id=str(message.message_id),
                    priority=ContextPriority.HISTORY,
                    role=(
                        ContextMessageRole.USER
                        if message.role is MessageRole.USER
                        else ContextMessageRole.ASSISTANT
                    ),
                    occurred_at=message.created_at,
                )
            )
        contributions.append(
            ContextContribution(
                kind=ContributionKind.CURRENT_REQUEST,
                content=user_message.content,
                source="message",
                source_id=str(user_message.message_id),
                priority=ContextPriority.REQUEST,
            )
        )
        return self._context_assembler.assemble(
            ContextRequest(
                session_id=run.session_id,
                run_id=run.run_id,
                contributions=tuple(contributions),
                character_limit=self._context_character_limit,
            )
        )

    async def _record_runner_event(self, run: RunRecord, item: AgentRunEvent) -> None:
        kind: EventKind
        payload: dict[str, JsonValue]
        if isinstance(item, TextDelta):
            kind, payload = EventKind.ASSISTANT_DELTA, {"text": item.text}
        elif isinstance(item, ToolRequested):
            kind = EventKind.TOOL_REQUESTED
            payload = {
                "tool_call_id": str(item.call_id),
                "name": item.name,
                "arguments": item.arguments,
            }
        elif isinstance(item, ToolStarted):
            kind = EventKind.TOOL_STARTED
            payload = {"tool_call_id": str(item.call_id), "name": item.name}
        elif isinstance(item, ToolCompleted):
            kind = EventKind.TOOL_COMPLETED
            payload = {
                "tool_call_id": str(item.call_id),
                "name": item.name,
                "truncated": item.truncated,
            }
        elif isinstance(item, ToolFailed):
            kind = EventKind.TOOL_FAILED
            payload = {
                "tool_call_id": str(item.call_id),
                "name": item.name,
                "error": _error_payload(item.error),
            }
        elif isinstance(item, UsageUpdated):
            return
        else:
            raise _runtime_error("agent.framework_failure", "The runner emitted an unknown event.")
        event = self._new_event(run.session_id, kind, payload, run_id=run.run_id)
        await self._persistence.append_event(to_stored_event(event))
        self._mark_event_committed(event)
        self._publisher.publish(event)

    async def _record_terminal_failure(
        self,
        run: RunRecord,
        kind: EventKind,
        status: RunStatus,
        error: ErrorInfo,
    ) -> None:
        terminal = self._new_event(
            run.session_id,
            kind,
            {"error": _error_payload(error)},
            run_id=run.run_id,
        )
        await self._persistence.terminate_run(
            run.run_id, status, to_stored_event(terminal), error
        )
        self._mark_event_committed(terminal)
        self._publisher.publish(terminal)

    async def _seed_sequence(self, session_id: SessionId) -> None:
        if session_id not in self._sequences:
            self._sequences[session_id] = await self._persistence.last_sequence(session_id)

    def _new_event(
        self,
        session_id: SessionId,
        kind: EventKind,
        payload: dict[str, JsonValue],
        *,
        run_id: RunId | None = None,
    ) -> RuntimeEvent:
        sequence = self._sequences.get(session_id)
        if sequence is None:
            raise _runtime_error(
                "runtime.sequence_uninitialized", "The event sequence is unavailable."
            )
        sequence += 1
        return RuntimeEvent(
            event_id=new_event_id(),
            session_id=session_id,
            run_id=run_id,
            sequence=sequence,
            occurred_at=self._clock.utc_now(),
            kind=kind,
            payload=payload,
        )

    def _mark_event_committed(self, event: RuntimeEvent) -> None:
        self._sequences[event.session_id] = event.sequence

    def _task_done(self, task: asyncio.Task[None]) -> None:
        self._tasks.discard(task)
        if not task.cancelled():
            task.exception()

    async def _shutdown(self, grace_seconds: float) -> None:
        if self._closed:
            return
        self._accepting = False
        states = list(self._active_by_run.values())
        for state in states:
            state.cancellation.cancel()
            state.task.cancel()
        if self._tasks:
            _, pending = await asyncio.wait(self._tasks, timeout=grace_seconds)
            for task in pending:
                task.cancel()
        await self._runner.close()
        await self._model.close()
        for callback in self._shutdown_callbacks:
            await callback(grace_seconds)
        await self._persistence.close()
        self._publisher.close()
        self._closed = True
