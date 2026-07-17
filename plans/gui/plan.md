# GUI Plan

## Final Vision

GUI is a responsive PyQt desktop client for Agentle's application boundary. It renders persisted session state and normalized runtime events and submits typed commands through `RuntimeClient`; widgets never know which model, runner, database, tool, or execution backend is active.

## Responsibilities

- Build the Phase 1 main window, transcript, prompt input, send/stop controls, and compact activity/error view.
- Convert user gestures into Runtime commands through an injected Qt-facing client adapter.
- Reduce session snapshots and ordered runtime events into immutable or clearly owned view state.
- Keep all widget mutation on the Qt main thread and keep model/tool/database work off it.
- Reflect starting, streaming, cancelling, completed, failed, and shutdown states without freezing.
- Initiate graceful runtime shutdown when the window closes and present a bounded closing state.

## Non-Responsibilities

- No direct model SDK, agent framework, persistence, tool, execution backend, filesystem, or subprocess invocation.
- No context assembly, run scheduling, retry logic, error classification, or authorization decisions.
- No backend-specific stream parsing or provider configuration objects in widgets.
- No dashboard, trace analytics, project editor, plugin manager, migration center, release UI, or multi-agent control in Phase 1.

## Phase 1 Concepts and Terminology

- **Runtime client:** the only application service visible to GUI controllers.
- **Qt runtime bridge:** adapter that moves commands to the Runtime asyncio worker and emits Qt signals containing Agentle receipts/events back on the GUI thread.
- **View state:** GUI-owned projection containing session ID, transcript rows, draft text, active run ID/status, activity rows, and displayable error.
- **Reducer:** deterministic function applying a session snapshot or next-sequence runtime event to view state.
- **Activity row:** concise model/tool/execution lifecycle item derived from normalized events, not a raw log viewer.
- **Closing state:** disabled input while Runtime completes/cancels work within its shutdown grace period.

## Minimum Public Contracts

- `MainWindow(runtime_client: QtRuntimeClient)` construction; all other concrete services are absent.
- `QtRuntimeClient` operations mirroring `create_session`, `submit_prompt`, `cancel_run`, `load_session`, and `shutdown` plus receipt/event/snapshot/shutdown-complete signals.
- `SessionViewState`, `TranscriptItem`, `ActivityItem`, and reducer functions owned by GUI.
- Mapping from structured `ErrorInfo` to a safe user message and optional diagnostic code.
- Main-window states: `idle`, `starting`, `running`, `cancelling`, `failed`, and `closing`.

The Qt bridge may import Runtime contracts and PyQt. Widgets import the bridge interface, not Runtime implementation classes.

## Dependencies

### Permitted internal dependencies

- Foundation IDs/errors and Runtime command/event/snapshot contracts through the Qt bridge.
- No dependency on concrete Agents, Models, Context, Tools, Execution, or Persistence packages.

### Permitted external dependencies

- PyQt6 only in Phase 1 GUI code.
- Python standard-library threading/queue primitives in the bridge.

The Runtime worker owns an asyncio loop in a dedicated thread. Phase 1 does not add an asyncio/Qt event-loop integration dependency.

## Future Extension Seams

- Add views/controllers that consume existing or deliberately extended runtime commands/events.
- Replace widgets without changing backend adapters because view state is event-derived.
- Add a project selector after Projects Phase 0/1 contracts are complete.
- Rich trace inspection may consume the persisted event journal later; it is not a dashboard framework.

## Phase 0 — Contracts and Boundaries

### Requirements

- [x] Define the Qt bridge, view state, reducer, GUI states, and close behavior.
- [x] Define the hard prohibition on direct backend/SDK/database/tool/subprocess access.
- [x] Define the dedicated runtime-thread boundary and main-thread widget rule.
- [x] Record unresolved Qt testing and close-timeout questions in `notes.md`.

### Non-Goals

- No widgets, generated UI files, theme system, dashboard, settings center, or project management UI.
- No direct async/provider/database integration in GUI.

### Acceptance Criteria

- [x] Every Phase 1 interaction maps to a Runtime command or event/snapshot.
- [x] The GUI dependency list excludes all concrete infrastructure and agentic libraries.
- [x] Event replay and live events use the same reducer semantics.
- [x] Responsiveness, cancellation, failure, and shutdown states have testable outcomes.

## Phase 1 — Functional Vertical Path

### Requirements

- [ ] Build one main window with transcript, multiline prompt, Send, Stop, status, and activity list.
- [ ] Create or load one session at startup through `QtRuntimeClient`.
- [ ] Disable Send while a session run is active; enable Stop until a terminal event arrives.
- [ ] Render assistant deltas incrementally and reconcile to the completed persisted message.
- [ ] Display tool/execution activity and safe structured failures without raw tracebacks or secrets.
- [ ] On close, request shutdown, wait asynchronously up to the GUI grace period, and only then destroy the runtime thread; present a force-close choice only after Runtime reports timeout.

### Non-Goals

- No multiple windows/sessions visible at once, rich Markdown/web view, attachments, project selector, settings editor, trace dashboard, tray mode, or packaging work.
- No GUI-side optimistic run completion or direct persistence replay query.

### Acceptance Criteria

- [ ] A user can submit a prompt, see streaming text, observe a native tool, cancel, and see terminal state without the window becoming unresponsive.
- [ ] Widget code has architecture tests forbidding imports of provider, runner-adapter, persistence-adapter, tool-implementation, execution-adapter, and subprocess modules.
- [ ] Reducer tests cover live/replayed events, duplicate events, sequence gaps, failure, cancellation, and completion.
- [ ] Closing during model or tool activity leaves no runtime thread/task active.
- [ ] An offscreen GUI smoke test completes with fake RuntimeClient and no network/database.

## Later Phases

Additional views follow completed application contracts. GUI expansion does not create a second path to providers or infrastructure.

## Related Decisions

- [ADR 0002](../../docs/decisions/0002-runtime-command-event-contract.md)
- [ADR 0004](../../docs/decisions/0004-qt-runtime-thread-boundary.md)

