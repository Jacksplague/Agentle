# Testing Notes

## Research

- Existing development dependencies cover lint, typing, async tests, and coverage. PyQt includes QtTest, so an additional GUI test helper can wait for an implementation spike.

## Rejected Approaches

- Default live-provider tests would be slow, costly, and non-hermetic.
- Timing tests based on arbitrary sleeps are unreliable for cancellation/shutdown behavior.
- Testing only the complete GUI path would obscure contract ownership and failure causes.

## Questions

- Which operating systems form the Phase 1 supported test matrix, especially for path and process-tree behavior?
- What maximum wall-clock duration should the offline check suite target?
- Which endpoint capability assumptions belong in the optional live smoke test?
- When the package graph grows, should the current focused AST import guard be replaced by a dedicated dependency-rule tool?

## Implementation Observations

- The first integration test should use a fake model transport but the real runner adapter if the framework permits it; otherwise contract-test the adapter separately and use a scripted runner for the full path.
- Native QApplication event processing is sufficient for the first offscreen smoke test; `pytest-qt` was not added.
- The implemented offline vertical integration uses a fake OpenAI SSE transport with the real Pydantic AI runner, `read_text`, local backend, SQLite journal, and Runtime replay.
