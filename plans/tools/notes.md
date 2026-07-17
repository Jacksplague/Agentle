# Tools Notes

## Research

- JSON Schema is the practical function-tool exchange format supported by the selected framework; Agentle definitions must retain only the subset actually exercised by Phase 1.

## Rejected Approaches

- Treating skills as executable tools erases the instruction/action boundary.
- Allowing tools to open files or subprocesses directly bypasses workspace confinement and backend replacement.
- Dynamic discovery and MCP are not needed to prove the native path.

## Questions

- What fields of tool input/output may be persisted without leaking sensitive file content?

## Implementation Observations

- `run_command` is blocked on a planned Policy authorization contract. It must not be smuggled in as a generic native tool during the first slice.
- `read_text` performs strict manual validation, defaults to 200 lines, caps requests at 500 lines and 65,536 bytes, and allows symlinks only when the resolved target remains inside the workspace.
- Runtime persists bounded lifecycle metadata and terminal output, not the full native tool result payload.
