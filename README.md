# Agentle

Agentle is a modular desktop agent host designed to integrate proven external systems for model access, agent orchestration, memory, tools, skills, sandboxed execution, and observability without rebuilding each subsystem from first principles.

The initial objective is a narrow, functional vertical path with stable internal contracts. Additional backends and modules will be added only after the first implementation works end to end.

## Initial vertical path

```text
PyQt GUI
  -> Runtime command/event layer
  -> Single-agent runner adapter
  -> OpenAI-compatible model adapter
  -> Native tool
  -> Local execution backend
  -> SQLite session and event persistence
```

Phase 1 starts with a read-only `read_text` tool through the local backend. Subprocess execution follows only after the Policy authorization boundary is planned and tested; the local backend is not presented as a security sandbox.

## Repository structure

- `ARCHITECTURE.md` — architectural boundaries and dependency rules
- `ROADMAP.md` — section-by-phase checklist
- `plans/` — final vision, phased requirements, contracts, and unresolved notes
- `src/agentle/` — application source packages
- `tests/` — unit, contract, integration, and end-to-end tests
- `docs/decisions/` — architecture decision records
- `AGENTS.md` — durable repository instructions for coding agents

## Clean development setup

Agentle requires Python 3.12 or newer. Runtime production dependencies have not yet been added; the commands below install only the scaffold and existing development tools.

PowerShell:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

POSIX shell:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e '.[dev]'
```

Install the existing optional GUI dependency only when working on GUI code:

```bash
python -m pip install -e '.[dev,gui]'
```

## Validation

Run the platform script:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\check.ps1
```

```bash
./scripts/check.sh
```

Or run the exact checks individually from the repository root:

```bash
python -m ruff check .
python -m mypy src
python -m pytest
```

The default suite must stay offline. Future live-provider smoke tests will be opt-in and excluded from these commands.

## Current status

Phase 0 planning is complete for Foundation, Runtime, Models, Agents, Context, Tools, Execution, Persistence, GUI, and Testing. Application runtime implementation has not started, and no Phase 1 item is complete.
