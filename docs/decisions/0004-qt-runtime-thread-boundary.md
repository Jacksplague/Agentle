# ADR 0004: Run asyncio Runtime behind a Qt signal bridge

- **Status:** Accepted
- **Date:** 2026-07-17
- **Owners:** Agentle maintainers

## Context

PyQt requires widget access on its main thread. Model streaming, SQLite work, tools, and cancellation are naturally asynchronous and must not block that thread. Adding a third-party Qt/asyncio loop bridge is not necessary to prove the first path.

## Decision

- Run Runtime's asyncio loop in one dedicated owned worker thread.
- Expose a thread-safe `RuntimeClient` and a PyQt `QtRuntimeClient` bridge. Commands cross to Runtime; receipts, snapshots, and normalized events return through queued Qt signals.
- Mutate widgets only on the Qt main thread.
- On window close, enter a closing state, submit `Shutdown`, and wait asynchronously for `shutdown-complete`. Runtime owns cancellation and resource close order.
- Do not let widgets hold futures, event loops, provider clients, repositories, tools, or subprocess handles.

## Consequences

- GUI responsiveness and backend independence have a clear testable boundary.
- Cross-thread ordering and shutdown require explicit bridge tests.
- The first implementation can avoid an additional loop-integration dependency.
- A later measured need may replace the bridge internally without changing Runtime commands/events.

## Alternatives considered

- **Run asyncio work on the Qt thread:** risks UI stalls and complicated reentrancy.
- **Use a third-party Qt/asyncio bridge immediately:** viable, but adds a dependency before native signal/queue composition is tested.
- **Let each widget create a worker:** fragments lifecycle and violates centralized Runtime supervision.

