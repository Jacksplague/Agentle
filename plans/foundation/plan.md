# Foundation Plan

## Final Vision

Foundation is the dependency-light vocabulary shared at Agentle's stable boundaries. It gives commands, events, adapters, and persisted records consistent identifiers, time values, cancellation signals, deadlines, and safe error descriptions without becoming a miscellaneous utilities package.

## Responsibilities

- Define opaque typed identifiers for sessions, runs, commands, events, tool calls, and executions.
- Define UTC timestamp, deadline, cancellation, and structured error primitives.
- Define cross-section configuration values, including `SecretRef` values that name a credential source without containing the credential.
- Provide small Python `Protocol` contracts such as `Clock` and `CancellationToken` where production and deterministic test implementations are both required.
- Establish naming, serialization, and error-code conventions used by public contracts.

## Non-Responsibilities

- No service locator, dependency-injection container, component registry, or plugin discovery.
- No application lifecycle, task scheduling, event publication, or persistence transaction handling.
- No model, agent, tool, execution, GUI, or database types merely because several modules import them.
- No secret storage or environment access; a composition-root adapter resolves `SecretRef` values.
- No wrappers around third-party APIs unless a cross-section Agentle contract requires one.

## Phase 1 Concepts and Terminology

- **Opaque identifier:** a UUID-backed string NewType whose kind cannot be accidentally exchanged with another identifier kind.
- **UTC timestamp:** a timezone-aware `datetime`; naive datetimes are invalid at public boundaries.
- **Deadline:** an absolute monotonic deadline propagated down a run. A child operation may shorten, but never extend, its parent's remaining time.
- **Cancellation token:** a read-only cooperative signal. Runtime owns cancellation; downstream code observes it and aborts promptly.
- **Error info:** a serializable, sanitized description containing `code`, `category`, `message`, `retryable`, and optional non-secret `details` and `cause_code`.
- **Secret reference:** a name such as `env:OPENAI_API_KEY`; its resolved value must never enter an event, exception message, log, or SQLite record.

## Minimum Public Contracts

- Identifier types: `SessionId`, `RunId`, `CommandId`, `EventId`, `ToolCallId`, and `ExecutionId`.
- `ErrorCategory`: `configuration`, `validation`, `provider`, `tool`, `execution`, `persistence`, `timeout`, `cancelled`, and `internal`.
- `ErrorInfo` and the base `AgentleError` conversion rule. Unknown exceptions become a sanitized `internal.unexpected` error at the runtime boundary.
- `Deadline` and `CancellationToken` protocols used by agent, tool, model-adapter, and execution operations.
- `SecretRef` plus a `SecretResolver` protocol used only during static application construction.
- `Clock` for UTC and monotonic time so timeout and event-order tests do not use wall-clock sleeps.

These contracts are typed dataclasses, enums, NewTypes, and protocols. They are not required to inherit from a shared base class.

## Dependencies

### Permitted internal dependencies

- None. Foundation is the lowest Agentle-owned package.

### Permitted external dependencies

- Python 3.12 standard library in Phase 1.
- A validation library may be used in configuration adapters, but Foundation's public objects must not require consumers to import it.

Foundation must not import PyQt, Pydantic AI, an OpenAI SDK, SQLite adapters, or subprocess code.

## Future Extension Seams

- Add a new identifier or error code when a real public contract needs it.
- Add secret resolvers through explicit composition, not discovery.
- Version serialized boundary objects at their owning section; do not add a universal schema system.

## Phase 0 — Contracts and Boundaries

### Requirements

- [x] Define the shared Phase 1 vocabulary and its ownership.
- [x] Limit Foundation's public contract to identifiers, time/control primitives, errors, and secret references used by at least two sections.
- [x] Define serialization and secret-redaction rules.
- [x] Record unresolved questions in `notes.md`.

### Non-Goals

- No implementation of the contracts.
- No general-purpose registry, dependency-injection framework, result monad, or universal base model.
- No production dependency selection.

### Acceptance Criteria

- [x] Every proposed public type has at least two named Phase 1 consumers.
- [x] Error, cancellation, deadline, timestamp, and secret handling have one documented meaning.
- [x] Foundation can remain independent of every other Agentle section.

## Phase 1 — Functional Vertical Path

### Requirements

- [ ] Implement and unit-test opaque ID factories and timezone validation.
- [ ] Implement `Deadline`, a cooperative cancellation token, and a deterministic test clock.
- [ ] Implement structured error conversion with explicit redaction tests.
- [ ] Implement environment-backed `SecretResolver` without persisting resolved values.

### Non-Goals

- No dynamic component loading or global configuration singleton.
- No broad utility collection, logging facade, or third-party exception hierarchy.

### Acceptance Criteria

- [ ] Static typing rejects interchange of distinct ID kinds.
- [ ] Cancellation and deadline tests are deterministic and do not sleep.
- [ ] An unknown exception crosses the runtime boundary only as sanitized `ErrorInfo`.
- [ ] Tests prove a resolved API key cannot appear in serialized errors or configuration snapshots.

## Later Phases

Foundation grows only when an implemented cross-section contract proves a need. It does not gain a plugin framework in advance of Phase 4 extension requirements.

## Related Decisions

- [ADR 0001](../../docs/decisions/0001-static-composition-and-owned-adapters.md)
- [ADR 0002](../../docs/decisions/0002-runtime-command-event-contract.md)
