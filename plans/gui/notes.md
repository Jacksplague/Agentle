# GUI Notes

## Research

- A dedicated Runtime asyncio thread with a Qt signal bridge avoids placing provider/tool work on the main thread and avoids another event-loop integration dependency in the first slice.

## Rejected Approaches

- Widgets calling async providers, repositories, or subprocesses directly violate the application boundary.
- A polling transcript that reads SQLite from widgets would create a second runtime path.
- A full trace dashboard is unnecessary for the initial activity list.

## Questions

- Should a future session-reload command be automatic after a sequence gap, or require an explicit user retry?
- Does a force-close choice need a new Runtime shutdown-timeout receipt, rather than being inferred from a GUI timer?

## Implementation Observations

- Live and replayed events must share one reducer, or restart behavior will diverge from the running UI.
- The implemented bridge owns an asyncio loop in one non-daemon Python thread and emits queued Qt signals; no additional event-loop package is needed.
- The first window uses a five-second shutdown grace, native QApplication event processing for its smoke test, and plain text rendering rather than Markdown/WebEngine.
- A sequence gap moves the reducer to a safe failed state and asks for reload; automatic replay remains unresolved.
