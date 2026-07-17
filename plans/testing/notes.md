# Testing Notes

## Research

- Existing development dependencies cover lint, typing, async tests, and coverage. PyQt includes QtTest, so an additional GUI test helper can wait for an implementation spike.

## Rejected Approaches

- Default live-provider tests would be slow, costly, and non-hermetic.
- Timing tests based on arbitrary sleeps are unreliable for cancellation/shutdown behavior.
- Testing only the complete GUI path would obscure contract ownership and failure causes.

## Questions

- Which operating systems form the Phase 1 supported test matrix, especially for path and process-tree behavior?
- Is QtTest sufficient for readable GUI tests, or does `pytest-qt` justify a new dev-only dependency?
- What maximum wall-clock duration should the offline check suite target?
- Which endpoint capability assumptions belong in the optional live smoke test?
- Should architecture boundaries be checked with a small source/import test or a dedicated dependency rule tool after code exists?

## Implementation Observations

- The first integration test should use a fake model transport but the real runner adapter if the framework permits it; otherwise contract-test the adapter separately and use a scripted runner for the full path.

