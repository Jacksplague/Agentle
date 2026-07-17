# Runtime Notes

## Research

- The simplest Phase 1 supervision model is one asyncio loop in one owned worker thread, one active task per session, and explicit constructor-injected collaborators.

## Rejected Approaches

- Publishing provider/framework events directly would couple GUI and storage to backend versions.
- An in-process message broker is unnecessary for one desktop process.
- Publishing before SQLite commit can show state that cannot be replayed after a crash.

## Questions

- What bounded subscriber queue size provides enough burst tolerance for text deltas without hiding a slow GUI?
- Should delta events be coalesced before persistence, and if so what maximum latency/size preserves useful streaming?
- On startup recovery, should `runtime.interrupted` terminal events simply take the next session sequence, or carry explicit recovery metadata as well?
- Is one active run globally simpler for the first slice than one active run per session, given the GUI exposes only one session?

## Implementation Observations

- Persistence failure while recording a terminal event needs a last-resort diagnostic path, because the normal committed-event contract cannot be satisfied.
