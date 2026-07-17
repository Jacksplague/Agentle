# Tools Notes

## Research

- JSON Schema is the practical function-tool exchange format supported by the selected framework; Agentle definitions must retain only the subset actually exercised by Phase 1.

## Rejected Approaches

- Treating skills as executable tools erases the instruction/action boundary.
- Allowing tools to open files or subprocesses directly bypasses workspace confinement and backend replacement.
- Dynamic discovery and MCP are not needed to prove the native path.

## Questions

- Will Phase 1 argument validation use dataclass/manual validation or the validation dependency already introduced by Pydantic AI?
- What default/max byte and line limits should `read_text` enforce?
- Should `read_text` reject all symlinks or allow those whose canonical targets remain inside the workspace?
- What fields of tool input/output may be persisted without leaking sensitive file content?

## Implementation Observations

- `run_command` is blocked on a planned Policy authorization contract. It must not be smuggled in as a generic native tool during the first slice.

