# Tools Plan

## Final Vision

Tools exposes named, schema-described actions to an agent runner and invokes Agentle-owned implementations through one controlled boundary. A tool describes an action; a skill supplies procedural knowledge; an execution backend performs local or remote operations. These remain separate concepts.

## Responsibilities

- Define tool metadata, input schemas, calls, invocation context, results, and errors.
- Maintain a statically composed Phase 1 catalog and enforce the selected agent's allow-list.
- Validate tool arguments before invoking an implementation.
- Invoke native tool implementations with deadline and cancellation propagation.
- Normalize output, size limits, and failures for the runner and Runtime events.
- Implement the first read-only workspace tool by delegating filesystem access to `ExecutionBackend`.

## Non-Responsibilities

- No model calls, agent loop, skill instructions, execution backend implementation, permission policy, GUI approval dialog, or event persistence.
- No MCP client/server in Phase 1 and no dynamic tool or plugin discovery.
- No direct subprocess or filesystem access inside tool contracts.
- No assumption that enabling a tool authorizes every call; Policy owns authorization decisions.

## Phase 1 Concepts and Terminology

- **Tool definition:** stable name, description, JSON-compatible input schema, output media type, and side-effect classification.
- **Tool catalog:** immutable set of enabled definitions/implementations assembled at startup.
- **Tool call:** runner-requested name, validated arguments, and `ToolCallId`.
- **Invocation context:** session/run IDs, workspace root, deadline, cancellation token, and an authorization result when required.
- **Tool result:** bounded text or JSON-compatible data plus truncation and metadata; it is not an execution result.
- **Native tool:** an Agentle-owned implementation registered explicitly at composition.
- **Skill:** instructions that may recommend a tool; it is never callable.
- **Execution backend:** the service a tool may use to touch the workspace or start a process.

## Minimum Public Contracts

- `ToolDefinition(name, description, input_schema, side_effect, output_media_type)`.
- `ToolCall(id, name, arguments)` and `ToolInvocationContext`.
- `ToolResult(content, media_type, truncated, metadata)` with a configured byte limit.
- `Tool` protocol exposing `definition` and `invoke(call, context) -> ToolResult`.
- `ToolCatalog.definitions_for(allowed_names)` and `ToolInvoker.invoke(call, context)`.
- Structured errors: `tool.unknown`, `tool.not_allowed`, `tool.invalid_arguments`, `tool.output_limit`, `tool.cancelled`, `tool.timeout`, and `tool.failed`.
- Phase 1 native `read_text(path, start_line?, max_lines?)`; paths are workspace-relative and results are UTF-8 text with explicit decoding errors.

JSON Schema is the exchange representation at the runner edge, but Phase 1 native implementations may use typed dataclasses internally. The schema is generated/validated in the adapter and never treated as Python code.

## Dependencies

### Permitted internal dependencies

- Foundation IDs, deadlines, cancellation, and errors.
- Execution's public backend contract for native tools.
- Policy's decision value only once side-effecting tools are implemented; no concrete policy service import in the tool domain.

### Permitted external dependencies

- Standard library in the tool domain.
- The agent framework adapter may translate definitions to its framework's function-tool API, but framework imports stay in Agents infrastructure.

## Future Extension Seams

- Add native tools by explicit composition and contract tests.
- Add an MCP tool adapter after the native vertical path; it must map MCP schemas/results to these contracts.
- Add approval-aware side-effect tools only after Policy Phase 0 defines the decision boundary.
- Tool catalog construction may later read project configuration, but it remains explicit rather than discovered from arbitrary packages.

## Phase 0 — Contracts and Boundaries

### Requirements

- [x] Define definitions, calls, invocation context, catalog, invoker, results, and errors.
- [x] Separate tools from skills, execution, agent orchestration, and authorization.
- [x] Specify one read-only native tool for the first slice.
- [x] Record unresolved schema and output-limit questions in `notes.md`.

### Non-Goals

- No tool implementation, MCP integration, dynamic registry, generated SDK, or plugin system.
- No `run_command` tool until the Policy planning boundary is complete.

### Acceptance Criteria

- [x] A runner can list and call allowed tools without knowing their implementations.
- [x] Invalid, unknown, and disallowed calls have distinct structured failures.
- [x] Tool contracts contain no subprocess, SQLite, GUI, or framework type.
- [x] The read-only first tool reaches the local execution backend through an injected protocol.

## Phase 1 — Functional Vertical Path

### Requirements

- [ ] Implement static catalog/invoker and strict argument validation.
- [ ] Implement `read_text` through the local execution backend with workspace confinement, line limits, byte limits, cancellation, deadline, and structured failures.
- [ ] Adapt catalog definitions/calls to Pydantic AI only inside the agent adapter.
- [ ] Emit enough invocation metadata for Runtime to create requested/started/completed/failed events without persisting unbounded content.
- [ ] After Policy Phase 0 is complete, add a separately reviewed `run_command(argv, cwd)` tool backed by Execution; it remains a Phase 1 item, not part of the first slice.

### Non-Goals

- No arbitrary shell string, `shell=True`, hidden tools, automatic skill installation, MCP, remote tools, or autonomous approval.
- No tool retry policy or parallel calls unless the selected framework requires and tests deterministic support.

### Acceptance Criteria

- [ ] The fake runner can call `read_text` and receive a bounded result through `ToolInvoker`.
- [ ] Absolute paths, traversal, symlink escape, invalid UTF-8, cancellation, timeout, and oversize output have contract tests.
- [ ] Only allow-listed definitions are exposed to the runner.
- [ ] A native tool can be replaced with a fake without changing Runtime or GUI.
- [ ] `run_command` remains absent until its Policy gate and approval tests exist.

## Later Phases

Phase 2 may add MCP and a second native tool family after the native contract is proven. Skills remain instruction packages and never become a tool-discovery mechanism.

## Related Decisions

- [ADR 0001](../../docs/decisions/0001-static-composition-and-owned-adapters.md)
- [ADR 0005](../../docs/decisions/0005-phase-1-local-execution-boundary.md)
