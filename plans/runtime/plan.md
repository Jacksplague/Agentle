# Runtime Plan

## Final Vision

Runtime is Agentle's application command and event boundary. It accepts user intent from a GUI or future client, coordinates one run through injected services, publishes backend-independent events, and owns task cancellation, deadlines, terminal state, and graceful process shutdown.

## Responsibilities

- Validate and dispatch application commands.
- Create and supervise run tasks and enforce one active run per session in Phase 1.
- Coordinate persistence, context assembly, the selected agent runner, tools, and execution through injected Agentle contracts.
- Assign per-session event sequence numbers and publish the canonical normalized event stream.
- Persist each event before making it visible to GUI subscribers.
- Convert failures at every adapter boundary to structured errors and exactly one terminal run event.
- Own cancellation requests, run deadlines, shutdown grace periods, and resource close order.

## Non-Responsibilities

- No GUI widgets or Qt event handling.
- No model SDK calls, prompt construction, agent loop, tool implementation, subprocess creation, or SQL statements.
- No global repository or provider lookup; all collaborators are constructor-injected.
- No autonomous agent selection, subagent switching, workflow graphs, or durable orchestration.
- No backend-specific events or exception objects in the public event stream.

## Phase 1 Concepts and Terminology

- **Command:** immutable user intent accepted once and identified by `CommandId`.
- **Receipt:** immediate acknowledgement containing the command ID and accepted/rejected status; it is not run completion.
- **Run:** one user prompt processed by one configured agent within one session.
- **Runtime event:** immutable, versioned envelope with `event_id`, `session_id`, optional `run_id`, strictly increasing per-session `sequence`, UTC `occurred_at`, `kind`, and typed payload.
- **Terminal event:** exactly one of `run.completed`, `run.cancelled`, or `run.failed`.
- **Event subscriber:** a bounded per-client queue. A slow GUI may be disconnected with a structured error but may recover the durable stream from persistence.
- **Graceful shutdown:** stop accepting commands, request cancellation, wait for a configured grace period, force-close remaining adapters, flush persistence, then stop the runtime worker.

## Minimum Public Contracts

### Commands

- `CreateSession(title: str | None)`
- `SubmitPrompt(session_id, text, agent_id, timeout_seconds)`
- `CancelRun(run_id)`
- `Shutdown(grace_seconds)`

### Client and events

- `RuntimeClient.submit(command) -> CommandReceipt`; the GUI-facing implementation is thread-safe and never exposes an asyncio or backend object.
- `RuntimeClient.subscribe() -> EventSubscription` and `load_session(session_id)` for replay and initial view state.
- Event kinds required by Phase 1: `session.created`, `run.started`, `assistant.delta`, `tool.requested`, `tool.started`, `tool.completed`, `tool.failed`, `execution.started`, `execution.output`, `execution.completed`, `execution.failed`, and the three terminal run kinds.
- `RuntimeEvent` schema version `1`; payloads are selected by `kind` and contain no provider object, raw exception, credential, or Qt value.

### Injected collaborators

- `AgentRunner`, `ContextAssembler`, `ToolInvoker`, session/run persistence repositories, `Clock`, and an application-owned event publisher.

## Dependencies

### Permitted internal dependencies

- Foundation contracts.
- Agents, Context, Tools, and Persistence public contracts. Runtime maps its canonical events to Persistence's storage record at the repository boundary.
- Execution events only through Tools or an injected execution-event bridge; Runtime does not import a concrete local backend.

### Permitted external dependencies

- Python `asyncio` and standard-library concurrency primitives.

Runtime must not import PyQt, Pydantic AI, OpenAI SDK types, SQLite modules, or concrete tools.

## Future Extension Seams

- New commands and event payload versions may be added explicitly while retaining replay support.
- A later scheduler may change concurrency policy behind the same command/event boundary.
- Durable workflows may consume the journal later; Phase 1 does not model workflow graphs.
- Alternate clients may receive the same runtime events without changing the coordinator.

## Phase 0 — Contracts and Boundaries

### Requirements

- [x] Define command, receipt, event envelope, payload, and terminal-state semantics.
- [x] Define persistence-before-publication ordering and bounded subscriber behavior.
- [x] Define cancellation, timeout, structured failure, and graceful shutdown behavior.
- [x] Define runtime dependencies without any concrete infrastructure imports.
- [x] Record unresolved questions in `notes.md`.

### Non-Goals

- No runtime implementation, durable workflow engine, plugin bus, or generalized message broker.
- No commands for project management, dashboards, release management, or migrations UI.

### Acceptance Criteria

- [x] The GUI can perform the Phase 1 flow using only `RuntimeClient`.
- [x] Every started run has exactly one specified terminal outcome.
- [x] Event ordering, replay, timeout, cancellation, and shutdown are testable without a live model.
- [x] No runtime contract contains a backend-specific or GUI-specific type.

## Phase 1 — Functional Vertical Path

### Requirements

- [x] Construct one runtime service from explicit dependencies at the application composition root.
- [x] Create/load a session, persist a user message, and start one run per submitted prompt.
- [x] Assemble context, invoke one runner, normalize its output, and stream committed events to GUI.
- [x] Route tool calls through `ToolInvoker`; never let the runner call native implementations directly.
- [x] Enforce run and child-operation deadlines and cooperative cancellation.
- [x] Reject a duplicate active run for the same session with `runtime.session_busy`.
- [x] On shutdown, reject new work, cancel active work, flush terminal state, and close runner, model, persistence, and worker resources in deterministic order.

### Non-Goals

- No parallel runs within one session, queued prompts, retry policy, resume-after-crash, multi-agent handoff, or autonomous agent choice.
- No in-process event history as a substitute for SQLite replay.

### Acceptance Criteria

- [x] A fake-backed run emits strictly increasing sequences from `run.started` to one terminal event.
- [x] The GUI receives no event that failed to persist.
- [x] Cancellation and timeout each reach terminal state within a bounded test deadline and cancel any active tool/execution operation.
- [x] Provider, tool, persistence, and unexpected failures appear as structured `run.failed` events.
- [x] Shutdown leaves no runtime worker, model request, tool task, or local process running.

## Later Phases

Phase 2 may add concurrency and a second runner. Durable/resumable workflows and multi-agent behavior belong to Phase 3. External event transports and plugins are Phase 4 concerns.

## Related Decisions

- [ADR 0001](../../docs/decisions/0001-static-composition-and-owned-adapters.md)
- [ADR 0002](../../docs/decisions/0002-runtime-command-event-contract.md)
- [ADR 0004](../../docs/decisions/0004-qt-runtime-thread-boundary.md)
