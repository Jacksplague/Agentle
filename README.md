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

Agentle requires Python 3.12 or newer. The first vertical slice pins its agent/model dependencies; install the GUI extra to run the desktop application and its offscreen smoke test.

PowerShell:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev,gui]"
```

POSIX shell:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e '.[dev,gui]'
```

For headless contract work, omit the `gui` extra:

```bash
python -m pip install -e '.[dev]'
```

## Configure and run

Agentle reads configuration from the process environment; it does not implicitly load `.env`. The API key may be a local endpoint's placeholder value, but it must be present.

PowerShell:

```powershell
$env:AGENTLE_MODEL_BASE_URL = "http://localhost:1234/v1"
$env:AGENTLE_MODEL_NAME = "your-model-name"
$env:AGENTLE_MODEL_API_KEY = "local"
python -m agentle
```

POSIX shell:

```bash
export AGENTLE_MODEL_BASE_URL='http://localhost:1234/v1'
export AGENTLE_MODEL_NAME='your-model-name'
export AGENTLE_MODEL_API_KEY='local'
python -m agentle
```

Optional `AGENTLE_WORKSPACE` selects the confined read workspace. `AGENTLE_DATA_DIR` selects the SQLite directory; otherwise Agentle uses `<workspace>/.agentle`.

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

The default suite stays offline. The live-provider smoke test is opt-in and excluded from these commands.

Run the opt-in provider diagnostic only with an endpoint configured as above:

```bash
python -m pytest -m live tests/live/test_openai_compatible_endpoint.py
```

## Current status

Phase 0 planning is complete for the initial ten sections. The first Phase 1 vertical slice is implemented: a PyQt command/event client, supervised single-agent runtime, pinned Pydantic AI/OpenAI-compatible adapter, confined `read_text`, and SQLite journal all run behind Agentle-owned contracts. Subprocess execution, Policy approval, memory retrieval, skills, MCP, multi-agent behavior, and dynamic plugins remain outside this slice.
