# Persistence Plan

## Final Vision

Persistence durably stores the user-visible transcript, run state, and canonical runtime event journal behind explicit repositories. SQLite is the Phase 1 implementation detail; Runtime receives repository instances and transaction operations rather than reaching a global database service.

## Responsibilities

- Define storage-facing records and repository/transaction contracts for sessions, messages, runs, and runtime events.
- Implement SQLite initialization, schema versioning, constraints, transactions, and clean connection shutdown.
- Preserve event envelope/payload data losslessly for replay in `(session_id, sequence)` order.
- Atomically create a run with its user message/start event and atomically finish it with terminal state, assistant message when successful, and terminal event.
- Detect and report corrupt, duplicate, out-of-order, and unsupported-schema data.

## Non-Responsibilities

- No runtime event generation, GUI view model, context ordering, memory retrieval, model history format, tool output policy, or observability dashboard.
- No global connection singleton, service locator, implicit ambient transaction, or imports from GUI widgets.
- No cloud sync, multi-user access, backup manager, migration center UI, analytics warehouse, or vector database in Phase 1.
- No storage of resolved credentials or raw provider objects.

## Phase 1 Concepts and Terminology

- **Session:** durable conversation container with ID, optional title, and timestamps.
- **Message:** durable user/assistant transcript item associated with a session and optionally a run.
- **Run record:** lifecycle summary for one prompt with agent/model IDs, status, timestamps, and terminal `ErrorInfo` when failed.
- **Event journal:** append-only storage records for canonical Runtime events; sequence is unique and strictly increasing per session.
- **Schema version:** integer database compatibility version managed on startup, distinct from runtime event schema version.
- **Repository set:** explicitly constructed `SessionRepository` and `RunJournal`; callers own and close their instance.
- **Committed-before-published:** Runtime may publish an event only after its persistence operation commits.

## Minimum Public Contracts

- Records: `SessionRecord`, `MessageRecord`, `RunRecord`, and `StoredRuntimeEvent` using Foundation IDs and UTC timestamps.
- `SessionRepository.create(session, created_event)`, `get(session_id)`, and `list_messages(session_id)`.
- `RunJournal.start(session_id, run, user_message, started_event)`.
- `RunJournal.append(event)` for nonterminal events with sequence validation.
- `RunJournal.complete(run_id, assistant_message, terminal_event)` and `terminate(run_id, terminal_event, error?)` as atomic operations.
- `RunJournal.list_events(session_id, after_sequence?)` and `recover_incomplete_runs()`.
- `Persistence.close()`; all contracts are asynchronous from callers' perspective even if the SQLite adapter serializes synchronous work on one owned worker.
- Structured errors: `persistence.unavailable`, `persistence.constraint`, `persistence.event_order`, `persistence.corrupt`, `persistence.schema_newer`, and `persistence.transaction`.

## Phase 1 Schema

- `schema_meta(version)`
- `sessions(id, title, created_at, updated_at)`
- `runs(id, session_id, agent_id, model_id, status, started_at, finished_at, error_json)`
- `messages(id, session_id, run_id, role, content, created_at)`
- `events(event_id, session_id, run_id, sequence, occurred_at, kind, schema_version, payload_json)`

Foreign keys are enabled. IDs are application-generated text UUIDs. Payload JSON is canonical UTF-8 JSON. SQLite runs in WAL mode when supported and has a configured busy timeout.

## Dependencies

### Permitted internal dependencies

- Foundation identifiers, errors, and timestamps.
- Runtime depends on Persistence records/protocols and maps `RuntimeEvent` to `StoredRuntimeEvent`. Persistence does not import Runtime services or event classes.

### Permitted external dependencies

- Python 3.12 `sqlite3`, JSON, and one explicitly owned worker/executor in Phase 1.
- No ORM or migration framework until schema complexity demonstrates a need.

## Future Extension Seams

- Add numbered, forward-only migration functions in code when the first schema change exists.
- Add a second repository adapter in Phase 2 and run it through contract tests.
- Add event compaction/export only after measured database growth; retain terminal transcript records.
- Memory may use separate tables/repositories later; it must not overload the session event journal contract.

## Phase 0 — Contracts and Boundaries

### Requirements

- [x] Define records, repositories, transaction boundaries, event ordering, replay, recovery, and close behavior.
- [x] Define the minimum SQLite schema and separate database/event versioning.
- [x] Prohibit implicit global persistence and credential/provider-object storage.
- [x] Record unresolved durability and migration questions in `notes.md`.

### Non-Goals

- No SQLite implementation, ORM selection, sync, backup subsystem, migration UI, or memory store.
- No promise of cross-process writers in Phase 1.

### Acceptance Criteria

- [x] The vertical path can create/load a session and durably journal a complete run through public contracts.
- [x] Start and terminal transitions have explicit atomic boundaries.
- [x] Runtime event replay preserves kind, schema version, payload, and per-session order.
- [x] Repository lifecycle is explicit and test fakes require no SQLite.

## Phase 1 — Functional Vertical Path

### Requirements

- [ ] Implement SQLite schema creation at version 1 with foreign keys, uniqueness constraints, WAL where available, and busy timeout.
- [ ] Implement explicit repositories on one owned database worker so GUI/runtime loops never block on SQLite calls.
- [ ] Implement start, append, complete/terminate, transcript load, replay, and incomplete-run recovery transactions.
- [ ] Mark nonterminal runs found at startup as failed with `runtime.interrupted` and a new terminal event.
- [ ] Flush and close the worker/connection during graceful shutdown.

### Non-Goals

- No editable migration center, ORM, event-sourcing framework, global repository, encryption layer, cloud sync, vector search, or analytics query API.
- No deletion/retention UI in the first slice.

### Acceptance Criteria

- [ ] Repository contract tests run against temporary SQLite and fakes.
- [ ] Duplicate/out-of-order sequences fail without a partial commit.
- [ ] A completed run atomically contains its final assistant message, status, and terminal event.
- [ ] Restart replay reconstructs the same transcript/runtime terminal state.
- [ ] Shutdown releases the database so a new process can open it immediately.

## Later Phases

The first real schema change introduces migration code and compatibility tests. A second adapter, export, retention, and richer query models follow demonstrated needs rather than a generic data platform.

## Related Decisions

- [ADR 0002](../../docs/decisions/0002-runtime-command-event-contract.md)
- [ADR 0006](../../docs/decisions/0006-sqlite-session-and-event-journal.md)
