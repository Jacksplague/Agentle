# Repository Instructions for Coding Agents

## Start Here

Before changing architecture or code, read `README.md`, `ARCHITECTURE.md`, `ROADMAP.md`, `pyproject.toml`, the affected `plans/*/plan.md` and `plans/*/notes.md`, and relevant records in `docs/decisions/`. Read every section plan when a change crosses responsibility boundaries.

## Architectural Boundaries

- Build the narrow Phase 1 vertical path before platform features.
- Keep external agentic systems behind Agentle-owned adapters. Do not reimplement model routing, agent orchestration, memory algorithms, tool protocols, or sandbox infrastructure without an accepted decision explaining why an adapter cannot work.
- The GUI uses Runtime commands, snapshots, and normalized events only. GUI code must not call model SDKs, agent frameworks, persistence adapters, tools, execution backends, filesystem/process APIs, or subprocesses.
- Runtime owns supervision, event normalization, cancellation, deadlines, structured terminal outcomes, and graceful shutdown.
- Keep Models, Agents, and orchestration distinct. Keep Memory retrieval and Context assembly distinct. Keep Tools, Skills, Policy, and Execution distinct.
- Persistence is explicitly constructed and injected; never add a global connection, repository, or ambient unit of work.
- Prefer small typed dataclasses/enums and Python protocols over deep inheritance.
- Use static composition in Phase 1. Do not add dynamic plugin discovery, autonomous subagent switching, dashboards, release systems, or migration-center UI.
- Treat the local execution backend as trusted host access, not a security sandbox. Do not implement `run_command` before the Policy Phase 0 authorization contract is complete.

## Planning and Decisions

- Each section plan is authoritative for responsibilities, contracts, dependencies, non-goals, and acceptance criteria. Put unresolved choices in that section's `notes.md`.
- Create or update an ADR for decisions that affect multiple sections, introduce a lasting dependency, or constrain replacement boundaries.
- Mark a Phase 0 roadmap item complete only when its plan and notes meet their acceptance criteria. Never mark Phase 1 work complete from planning alone.
- Do not add production dependencies without an implementation need, adapter contract, evaluation notes, and any cross-cutting ADR. Keep external imports inside adapters.

## Development Practice

- Preserve unrelated user changes and keep edits scoped to the requested section.
- Add tests at the owning boundary: unit tests for domain behavior, reusable contract tests for adapters, offline integration tests for wiring, and a minimal offscreen GUI smoke test.
- Default checks must not require network, credentials, Docker, or an interactive display. Use synchronization primitives and bounded waits instead of arbitrary sleeps.
- Never persist or emit resolved secrets, raw third-party exceptions, framework objects, or unbounded model/tool output.
- Maintain cancellation, timeout, structured error, and `close()` behavior whenever a public async operation is introduced.

## Validation

From an activated Python 3.12+ environment with `.[dev]` installed, run:

```bash
python -m ruff check .
python -m mypy src
python -m pytest
```

The PowerShell and POSIX wrappers are `scripts/check.ps1` and `scripts/check.sh`. Keep their commands module-based, fail-fast, and equivalent. On a machine with restrictive Windows PowerShell policy, use `powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\check.ps1` for that process only.
