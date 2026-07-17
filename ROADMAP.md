# Agentle Roadmap

Each checkbox links to the authoritative section plan. Detailed implementation notes remain in that section's `notes.md` file.

## Phase 0 — Contracts and Boundaries

- [x] [Foundation](plans/foundation/plan.md#phase-0--contracts-and-boundaries)
- [x] [Runtime](plans/runtime/plan.md#phase-0--contracts-and-boundaries)
- [ ] [Projects](plans/projects/plan.md#phase-0--contracts-and-boundaries)
- [x] [Persistence](plans/persistence/plan.md#phase-0--contracts-and-boundaries)
- [x] [Models](plans/models/plan.md#phase-0--contracts-and-boundaries)
- [x] [Agents](plans/agents/plan.md#phase-0--contracts-and-boundaries)
- [x] [Context](plans/context/plan.md#phase-0--contracts-and-boundaries)
- [ ] [Memory](plans/memory/plan.md#phase-0--contracts-and-boundaries)
- [x] [Tools](plans/tools/plan.md#phase-0--contracts-and-boundaries)
- [ ] [Skills](plans/skills/plan.md#phase-0--contracts-and-boundaries)
- [x] [Execution](plans/execution/plan.md#phase-0--contracts-and-boundaries)
- [x] [GUI](plans/gui/plan.md#phase-0--contracts-and-boundaries)
- [ ] [Observability](plans/observability/plan.md#phase-0--contracts-and-boundaries)
- [ ] [Policy](plans/policy/plan.md#phase-0--contracts-and-boundaries)
- [ ] [Integrations](plans/integrations/plan.md#phase-0--contracts-and-boundaries)
- [x] [Testing](plans/testing/plan.md#phase-0--contracts-and-boundaries)
- [ ] [Distribution](plans/distribution/plan.md#phase-0--contracts-and-boundaries)

## Phase 1 — Functional Vertical Path

The first implementation slice is one statically composed workspace/session: a minimal PyQt window submits `CreateSession`, `SubmitPrompt`, `CancelRun`, and `Shutdown` through the Qt Runtime bridge; Runtime assembles application/agent instructions plus persisted history; one pinned Pydantic AI adapter uses one OpenAI-compatible Chat Completions endpoint; the agent may call only the native read-only `read_text` tool through the confined local execution backend; SQLite stores sessions, messages, runs, and committed normalized events; offline unit/contract/integration and offscreen GUI tests cover streaming, tool use, replay, failure, cancellation, timeout, and shutdown. Subprocesses, Policy approval UI, project selection, memory retrieval, skills, MCP, second backends, and dynamic plugins are outside this slice.

- [x] [Foundation](plans/foundation/plan.md#phase-1--functional-vertical-path)
- [x] [Runtime](plans/runtime/plan.md#phase-1--functional-vertical-path)
- [ ] [Projects](plans/projects/plan.md#phase-1--functional-vertical-path)
- [ ] [Persistence](plans/persistence/plan.md#phase-1--functional-vertical-path)
- [x] [Models](plans/models/plan.md#phase-1--functional-vertical-path)
- [x] [Agents](plans/agents/plan.md#phase-1--functional-vertical-path)
- [x] [Context](plans/context/plan.md#phase-1--functional-vertical-path)
- [ ] [Memory](plans/memory/plan.md#phase-1--functional-vertical-path)
- [ ] [Tools](plans/tools/plan.md#phase-1--functional-vertical-path)
- [ ] [Skills](plans/skills/plan.md#phase-1--functional-vertical-path)
- [ ] [Execution](plans/execution/plan.md#phase-1--functional-vertical-path)
- [ ] [GUI](plans/gui/plan.md#phase-1--functional-vertical-path)
- [ ] [Observability](plans/observability/plan.md#phase-1--functional-vertical-path)
- [ ] [Policy](plans/policy/plan.md#phase-1--functional-vertical-path)
- [ ] [Integrations](plans/integrations/plan.md#phase-1--functional-vertical-path)
- [ ] [Testing](plans/testing/plan.md#phase-1--functional-vertical-path)
- [ ] [Distribution](plans/distribution/plan.md#phase-1--functional-vertical-path)

## Phase 2 — Prove Modularity

- [ ] Add second model provider
- [ ] Add second execution backend
- [ ] Add second memory provider
- [ ] Add MCP tool provider
- [ ] Add second agent/orchestration adapter
- [ ] Add project switching and backend selection
- [ ] Add provider contract suites

## Phase 3 — Advanced Agent Behavior

- [ ] Multi-agent handoffs
- [ ] Durable and resumable workflows
- [ ] Long-term memory and consolidation
- [ ] Automatic skill selection
- [ ] Context compression and token budgeting
- [ ] Docker sandboxing
- [ ] Advanced trace inspection

## Phase 4 — Extensibility and Ecosystem

- [ ] External plugin discovery and installation
- [ ] Compatibility and version negotiation
- [ ] Remote workers and execution backends
- [ ] Shared skill repositories
- [ ] IDE integration
- [ ] Extension development kit
