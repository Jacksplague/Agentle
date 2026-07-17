# Architecture Decision Records

Use this directory for decisions that materially affect the repository or multiple planning sections.

Suggested filename format:

```text
0001-short-decision-title.md
```

Suggested status values: Proposed, Accepted, Superseded, Rejected.

## Decision index

- [0001 — Use static composition and Agentle-owned adapters](0001-static-composition-and-owned-adapters.md)
- [0002 — Make Runtime commands and durable normalized events the application boundary](0002-runtime-command-event-contract.md)
- [0003 — Use Pydantic AI behind paired Phase 1 agent/model adapters](0003-pydantic-ai-phase-1-adapter.md)
- [0004 — Run asyncio Runtime behind a Qt signal bridge](0004-qt-runtime-thread-boundary.md)
- [0005 — Treat local execution as trusted host access and stage subprocess support](0005-phase-1-local-execution-boundary.md)
- [0006 — Persist transcripts and the normalized event journal in explicit SQLite repositories](0006-sqlite-session-and-event-journal.md)
