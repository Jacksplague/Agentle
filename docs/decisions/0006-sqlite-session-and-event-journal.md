# ADR 0006: Persist transcripts and the normalized event journal in explicit SQLite repositories

- **Status:** Accepted
- **Date:** 2026-07-17
- **Owners:** Agentle maintainers

## Context

Phase 1 requires local session and event persistence, restart replay, and nonblocking GUI/runtime behavior. The schema is small and does not justify an ORM, migration product, or global database service.

## Decision

- Use Python's SQLite driver behind explicit asynchronous repository contracts and one adapter-owned database worker/connection.
- Store sessions, runs, user/assistant messages, and canonical runtime events in schema version 1.
- Enforce foreign keys and unique `(session_id, sequence)` ordering. Use WAL when supported and a configured busy timeout.
- Atomically store run start with the user message/start event and run completion with assistant message/status/terminal event.
- Keep database schema version separate from runtime event schema version.
- Construct and close repositories explicitly; no global connection or ambient transaction.
- Add numbered forward migrations only when the first schema change exists.

## Consequences

- Default development needs no database service or new production dependency.
- Runtime can replay backend-neutral events and load a clean transcript.
- Synchronous SQLite work is isolated from the Runtime/Qt threads but serialized by one worker.
- Cross-process writers, cloud sync, encryption, and high-volume analytics are not supported in Phase 1.

## Alternatives considered

- **ORM/async SQLite dependency now:** extra abstraction/dependency without schema complexity.
- **Persist only transcript messages:** insufficient for runtime replay and activity/error recovery.
- **Persist framework-native messages/events:** violates adapter isolation and complicates replacement.
- **Global repository singleton:** hides lifecycle and test isolation.
