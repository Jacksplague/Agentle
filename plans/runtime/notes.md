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
- Should `runtime.interrupted` later carry recovery-process metadata beyond its next committed session sequence and structured error?

## Implementation Observations

- Persistence failure while recording a terminal event needs a last-resort diagnostic path, because the normal committed-event contract cannot be satisfied.
- Runtime enforces one active run per session. The GUI exposes one session, but the contract does not create an unnecessary global run lock.
- Sequence numbers advance in memory only after the matching persistence operation succeeds; a failed delta write can therefore be replaced by the next contiguous terminal event.
