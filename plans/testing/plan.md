# Testing Plan

## Final Vision

Testing protects Agentle's responsibility boundaries and end-to-end behavior with fast unit tests, reusable adapter contract suites, integration tests built from fakes, and a small offscreen GUI smoke test. Live model tests are opt-in diagnostics, never prerequisites for the default suite.

## Responsibilities

- Define test layers, markers, fixtures, fakes, contract suites, and default validation commands.
- Verify public behavior for streaming, event ordering, persistence, errors, cancellation, timeouts, and shutdown.
- Enforce dependency rules with targeted import/architecture tests.
- Provide deterministic clocks, cancellation controls, fake runner/model/tool/backend/repositories, and temporary SQLite fixtures.
- Keep default tests offline, hermetic, and suitable for Windows and POSIX CI.

## Non-Responsibilities

- No production fallback behavior, runtime observability dashboard, release qualification system, benchmark farm, or external-provider uptime check.
- No tests coupled to private framework event classes except inside that adapter's tests.
- No broad mocking of internals when a public fake/contract test expresses the boundary.
- No mandatory credentials, network, Docker, or installed desktop display for default validation.

## Phase 1 Concepts and Terminology

- **Unit test:** one owner section with collaborators replaced by simple fakes.
- **Contract suite:** reusable behavioral tests every implementation of a protocol must pass.
- **Integration test:** several Agentle sections wired together through public contracts.
- **End-to-end smoke test:** offscreen PyQt window through Runtime with deterministic fake model transport and temporary SQLite.
- **Live test:** explicitly marked network test using user configuration; excluded by default.
- **Architecture test:** static import/package assertion enforcing dependency prohibitions.
- **Deterministic async test:** uses controllable fakes/events and bounded waits, not arbitrary sleeps.

## Minimum Public Contracts

Testing does not add production contracts. It provides test support:

- `FakeClock`, `FakeCancellationToken`, `ScriptedAgentRunner`, `FakeModelBinding`, `FakeTool`, `FakeExecutionBackend`, and in-memory repository fakes.
- Contract suite entry points for `AgentRunner`, `ModelAdapter`, `ToolInvoker`, `ExecutionBackend`, and Persistence repositories.
- Pytest markers: `integration`, `gui`, `live`, and `slow`; `live` and `slow` are excluded from the default command.
- Validation entry points `scripts/check.ps1` and `scripts/check.sh`, both using module-based tool invocation.

## Dependencies

### Permitted internal dependencies

- Tests may import public contracts and the concrete adapter under test.
- End-to-end tests may use the composition root with explicit test configuration.
- Production packages must never import `tests` or test-support packages.

### Permitted external dependencies

- Existing dev tools: pytest, pytest-asyncio, pytest-cov, Ruff, and mypy.
- A Qt testing helper may be proposed during Phase 1 only if native Qt test utilities prove insufficient; it is not added in Phase 0.
- No new production dependency for testing.

## Future Extension Seams

- Each second adapter joins its existing contract suite.
- Add recorded provider fixtures only after redaction/licensing review.
- Add performance or migration suites when corresponding production behavior exists.
- CI matrix and release gates belong to later distribution work, not this Phase 0 section.

## Phase 0 — Contracts and Boundaries

### Requirements

- [x] Define unit, contract, integration, GUI smoke, live, and architecture test layers.
- [x] Define deterministic cancellation/timeout/shutdown testing and required fakes.
- [x] Define offline default checks and opt-in live behavior.
- [x] Record unresolved GUI/platform coverage questions in `notes.md`.

### Non-Goals

- No runtime test implementation, CI platform, release gate, dashboard, benchmark, or new dependency.
- No coverage percentage target before Phase 1 code exists.

### Acceptance Criteria

- [x] Every Phase 1 public adapter contract has a named test strategy.
- [x] The complete vertical path can be tested without network credentials.
- [x] Cancellation, timeout, error, persistence ordering, and shutdown criteria use bounded deterministic assertions.
- [x] Both check scripts invoke Ruff, mypy, and pytest as Python modules.

## Phase 1 — Functional Vertical Path

### Requirements

- [x] Add unit tests alongside each implemented section contract and state transition.
- [ ] Add reusable contract suites for runner, model adapter, tools, execution, and repositories.
- [x] Add an offline integration test: prompt to fake Pydantic-compatible transport, native `read_text`, SQLite journal, and normalized event replay.
- [x] Add cancellation tests during model streaming and tool execution plus timeout and persistence-failure cases.
- [x] Add graceful-shutdown tests for active and idle runtime states.
- [x] Add architecture import tests and an offscreen PyQt smoke test.
- [x] Keep a live endpoint smoke test under `@pytest.mark.live`, excluded by default.

### Non-Goals

- No exhaustive GUI visual testing, provider certification matrix, load testing, fuzzing program, release-management suite, or Docker requirement.
- No sleep-based timing assertions where synchronization primitives can prove the state.

### Acceptance Criteria

- [x] `python -m ruff check .`, `python -m mypy src`, and default `python -m pytest` pass offline.
- [x] Tests fail if GUI imports a prohibited backend or if an adapter leaks its external types.
- [x] The integration test proves persist-before-publish ordering and exact terminal-event semantics.
- [x] Timeout/cancellation/shutdown tests assert no leaked tasks, threads, connections, or child processes.
- [x] The GUI smoke test works in an offscreen environment on the supported platforms.

## Later Phases

Phase 2 broadens contract suites to second implementations. Coverage thresholds, performance tests, CI matrices, and release qualification follow real code and distribution targets.

## Related Decisions

- [ADR 0002](../../docs/decisions/0002-runtime-command-event-contract.md)
- [ADR 0004](../../docs/decisions/0004-qt-runtime-thread-boundary.md)
