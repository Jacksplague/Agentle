# ADR 0005: Treat local execution as trusted host access and stage subprocess support

- **Status:** Accepted
- **Date:** 2026-07-17
- **Owners:** Agentle maintainers

## Context

The vertical path requires one local execution backend, but a host subprocess is not a sandbox. Side-effecting command execution also needs authorization owned by Policy, whose Phase 0 plan is not part of the ten sections completed here.

## Decision

- Define one backend-neutral `ExecutionBackend` for bounded file reads and later argv-based processes.
- Implement `read_text` with canonical workspace confinement as the first slice, proving Tool-to-Execution composition without granting process authority.
- Defer `run_command` implementation until Policy Phase 0 defines an authorization value tied to exact argv, canonical cwd, environment additions, and expiry.
- When implemented later in Phase 1, accept argv only, never `shell=True`; propagate cancellation/deadline, bound output/environment, and terminate the process tree on shutdown.
- Label the local backend trusted host execution. Select a proven sandbox/container backend later rather than constructing isolation from path checks and subprocess flags.

## Consequences

- The first slice still traverses the required local backend through a useful native tool.
- Arbitrary command execution cannot appear before its approval boundary is planned and tested.
- Local development execution has explicit trust limitations.
- Phase 2 can introduce a real isolated backend behind the same contract.

## Alternatives considered

- **Ship unrestricted command execution first:** unsafe and conflicts with Policy ownership.
- **Call the local process adapter a sandbox:** false security claim.
- **Build container isolation now:** exceeds the vertical-path scope and risks reimplementing sandbox infrastructure.

