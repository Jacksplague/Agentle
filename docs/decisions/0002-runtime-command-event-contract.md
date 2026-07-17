# ADR 0002: Make Runtime commands and durable normalized events the application boundary

- **Status:** Accepted
- **Date:** 2026-07-17
- **Owners:** Agentle maintainers

## Context

PyQt needs responsive streaming updates while SQLite must provide reliable restart/replay. Provider and framework event shapes are backend-specific. If UI and storage consume different representations, behavior will diverge.

## Decision

- The GUI submits Agentle commands only through `RuntimeClient`.
- Runtime emits one canonical versioned `RuntimeEvent` envelope with Agentle-owned payloads, UTC timestamps, correlation IDs, and a strictly increasing per-session sequence.
- Runtime maps runner/tool/execution activity into this schema and guarantees exactly one terminal run event.
- Persist each canonical event before publishing it to live subscribers. Start and terminal run transitions use the atomic journal operations defined by Persistence.
- Use bounded subscriber queues. A slow subscriber may reconnect and replay committed events rather than applying unbounded backpressure to the run.
- Credentials, raw exceptions, external objects, and unbounded tool/model content are forbidden in events.

## Consequences

- Live UI and restart replay share the same event semantics.
- SQLite failure is a run correctness failure, not silent observability loss.
- Persisting every text delta may create write volume; coalescing policy remains an implementation question but cannot violate ordering or durability.
- Event schema changes require explicit versioning and compatibility tests.

## Alternatives considered

- **Publish before commit:** lower latency but can display unrecoverable state.
- **Store raw framework events:** easier adapter code but permanently couples storage and GUI to a framework.
- **Use an external message broker:** unnecessary for one desktop process.
