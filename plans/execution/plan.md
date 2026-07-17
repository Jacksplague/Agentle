# Execution Plan

## Final Vision

Execution provides explicit, cancellable operations against a configured workspace through replaceable backends. Phase 1's local backend is an operating-system process/filesystem adapter, not a security sandbox; Agentle will integrate a proven sandbox backend later rather than claiming that path checks or subprocess flags provide isolation.

## Responsibilities

- Define backend-neutral filesystem/process requests, streamed events, results, and lifecycle.
- Resolve workspace-relative paths and prevent lexical, canonical, and symlink escape.
- Implement bounded local file reads for the first vertical slice.
- Implement asynchronous argv-based local process execution later in Phase 1, after authorization is supplied.
- Propagate deadlines/cancellation, bound captured output, terminate process trees, and report exit metadata.
- Close active operations during Runtime shutdown.

## Non-Responsibilities

- No tool names/schemas, skill instructions, model/agent behavior, permission decisions, or GUI prompts.
- No assertion that the local backend is a sandbox or safe for untrusted commands.
- No shell command parsing, `shell=True`, container management, SSH, remote workers, or sandbox implementation in the first slice.
- No persistent execution history; Runtime events and Persistence own durable records.

## Phase 1 Concepts and Terminology

- **Workspace:** one canonical root supplied at composition; every filesystem path and process working directory must remain below it.
- **Execution backend:** injected protocol that performs typed operations and owns their cancellation/close behavior.
- **File read request:** workspace-relative path, optional starting line, line limit, and byte limit.
- **Process request:** non-empty argv sequence, workspace-relative working directory, allow-listed environment additions, timeout, and output limit.
- **Execution event:** backend-neutral `Started`, `Output`, and terminal `Completed`/`Failed` values consumed by Tools/Runtime.
- **Authorization:** immutable decision from Policy tied to the requested operation. It permits an attempt but does not bypass backend confinement.
- **Local backend:** direct host filesystem/process access. It is trusted development execution, not isolation.

## Minimum Public Contracts

- `FileReadRequest(path, start_line, max_lines, max_bytes)` and `FileReadResult(text, lines, truncated)`.
- `ProcessRequest(argv, cwd, environment, timeout_seconds, max_output_bytes, authorization)`.
- `ExecutionEvent` variants with `execution_id`, stream (`stdout`/`stderr`), chunk, exit code, signal/termination reason, duration, and truncation state as applicable.
- `ExecutionBackend.read_text(request, control) -> FileReadResult`.
- `ExecutionBackend.run_process(request, control) -> AsyncIterator[ExecutionEvent]` and `close(grace_seconds)`.
- Structured errors: `execution.path_outside_workspace`, `execution.path_not_found`, `execution.decode`, `execution.not_authorized`, `execution.spawn`, `execution.output_limit`, `execution.timeout`, `execution.cancelled`, and `execution.termination`.

Phase 1 process requests use argv and never a command-line string. Environment starts from a minimal documented allow-list; secrets are not inherited by default.

## Dependencies

### Permitted internal dependencies

- Foundation IDs, deadlines, cancellation, and errors.
- Policy authorization value for `run_process`; the backend does not call a global policy service.
- Tools may depend on this contract; Execution never imports Tools.

### Permitted external dependencies

- Python 3.12 `pathlib`, `asyncio`, and platform-specific standard-library process primitives.
- A proven sandbox/container library is deferred; when selected it must implement this adapter contract.

Execution must not import PyQt, Pydantic AI, provider SDKs, or persistence adapters.

## Future Extension Seams

- Add a sandbox/container backend after evaluating process-tree termination, mount confinement, networking, and platform support.
- Add a second backend in Phase 2 to exercise the common contract.
- Extend operation types only for an implemented tool; do not pre-model remote job systems.
- Platform-specific local helpers may sit behind one `LocalExecutionBackend` without changing callers.

## Phase 0 — Contracts and Boundaries

### Requirements

- [x] Define file/process request, event, result, authorization, error, cancellation, and close semantics.
- [x] State explicitly that the local backend is not a sandbox.
- [x] Define workspace confinement, output bounds, environment, and argv-only rules.
- [x] Split first-slice read access from later Phase 1 authorized process execution.
- [x] Record platform and process-tree questions in `notes.md`.

### Non-Goals

- No backend implementation, sandbox, container, remote worker, terminal emulator, or command parser.
- No permission policy or approval workflow design in this section.

### Acceptance Criteria

- [x] Tools can use the backend without accessing local filesystem/process APIs directly.
- [x] Every operation accepts a deadline/cancellation signal and has a terminal result.
- [x] Local trust limitations and the Policy dependency for processes are explicit.
- [x] Backend contracts contain no tool, agent, GUI, or database type.

## Phase 1 — Functional Vertical Path

### Requirements

- [x] Implement workspace-canonicalized, symlink-safe, bounded UTF-8 `read_text` for the first slice.
- [x] Track active operations and make `close()` cancel/wait within a grace period.
- [ ] After Policy Phase 0, implement argv-only `asyncio` subprocess execution with separate stdout/stderr streaming, timeout, cancellation, output cap, exit metadata, and process-tree termination on Windows and POSIX.
- [ ] Do not inherit the complete parent environment; pass only baseline variables and explicit allow-listed additions.
- [ ] Convert platform exceptions to structured errors without including sensitive environment values.

### Non-Goals

- No security claim, shell strings, interactive PTY, elevation, container, network isolation, resource quotas beyond timeout/output, or remote execution.
- No subprocess path in the first implementation slice.

### Acceptance Criteria

- [x] File contract tests cover traversal, absolute paths, symlink escape, missing files, UTF-8 errors, line/byte bounds, cancellation, and close.
- [ ] Later process tests cover stdout/stderr ordering per stream, nonzero exit, spawn failure, timeout, cancellation, output overflow, and no surviving child process.
- [ ] A fake backend passes the same tool-facing contract without platform access.
- [ ] No process starts without a matching authorization value.

## Later Phases

Phase 2 selects a second, proven isolated backend and uses the same contract suite. Rich terminals, remote workers, and sandbox policy are later work driven by actual tools.

## Related Decisions

- [ADR 0001](../../docs/decisions/0001-static-composition-and-owned-adapters.md)
- [ADR 0005](../../docs/decisions/0005-phase-1-local-execution-boundary.md)
