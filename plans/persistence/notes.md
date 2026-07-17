# Persistence Notes

## Research

- The standard-library SQLite driver plus one owned worker can keep blocking database work off the runtime loop without adding an ORM or async database dependency.
- WAL improves normal desktop read/write concurrency but may not be appropriate on every filesystem, so startup must detect/fallback cleanly.

## Rejected Approaches

- A process-global connection/repository hides lifecycle and makes tests interfere.
- Storing only framework message JSON would couple transcript recovery to one agent library.
- An event-sourcing framework and migration center are disproportionate to five Phase 1 tables.

## Questions

- What batching/coalescing policy balances durable text deltas against SQLite write volume?
- Should session titles remain null/manual in Phase 1 or derive deterministically from the first prompt?
- What busy timeout and WAL fallback are appropriate for workspaces on network/removable filesystems?
- Is `payload_json` canonicalization needed byte-for-byte, or is semantic JSON equivalence sufficient?

## Implementation Observations

- Persist-before-publish makes SQLite availability part of run correctness; disk-full and locked-database tests are required.
- Static composition calls `RuntimeService.recover_interrupted_runs()` before the GUI bridge becomes ready; recovery appends `runtime.interrupted` as the next committed per-session event.
- SQLite uses a 5,000 ms busy timeout and attempts WAL with DELETE-journal fallback.
