# GUI Notes

## Research

- A dedicated Runtime asyncio thread with a Qt signal bridge avoids placing provider/tool work on the main thread and avoids another event-loop integration dependency in the first slice.

## Rejected Approaches

- Widgets calling async providers, repositories, or subprocesses directly violate the application boundary.
- A polling transcript that reads SQLite from widgets would create a second runtime path.
- A full trace dashboard is unnecessary for the initial activity list.

## Questions

- Should the bridge use `QThread` ownership or a Python thread with queued Qt signals after a minimal shutdown/profiling spike?
- What GUI shutdown grace period is understandable before presenting a force-close option?
- Is native QtTest sufficient for Phase 1, or should `pytest-qt` be added to dev dependencies during implementation?
- How should sequence gaps be presented while an automatic persisted-event replay is in progress?
- Which Markdown subset, if any, is safe and necessary for the first transcript view?

## Implementation Observations

- Live and replayed events must share one reducer, or restart behavior will diverge from the running UI.

