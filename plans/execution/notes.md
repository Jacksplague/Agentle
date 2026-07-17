# Execution Notes

## Research

- `asyncio` supports subprocess streams but cross-platform process-tree termination, Windows job objects, and inherited-handle behavior require an implementation spike.
- Canonical path checks must occur after resolving symlinks/junctions and again at open time where practical to reduce time-of-check/time-of-use gaps.

## Rejected Approaches

- Calling the local backend a sandbox is misleading; host subprocesses share the user's permissions.
- Shell strings and `shell=True` add quoting/injection ambiguity without a Phase 1 requirement.
- Building custom container isolation before the native vertical path would reimplement sandbox infrastructure.

## Questions

- Which proven cross-platform process-tree helper should be adopted if the standard library cannot reliably terminate descendants?
- What minimal baseline environment variables are required on Windows, macOS, and Linux?
- What exact immutable Policy authorization fields bind approval to argv, cwd, and environment?
- Should output overflow terminate the process or continue execution while discarding further output?
- Are workspace junctions on Windows handled identically to symlinks by the chosen canonicalization strategy?

## Implementation Observations

- File-read support is intentionally the first implementation slice; subprocess implementation waits for Policy Phase 0 and platform termination tests.

