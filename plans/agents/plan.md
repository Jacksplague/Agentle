# Agents Plan

## Final Vision

Agents owns declarative single-agent behavior and the adapter that delegates the model/tool loop to a proven agentic framework. It presents backend-neutral run inputs and event outputs to Runtime while keeping models, context assembly, and orchestration as distinct concepts.

## Responsibilities

- Define an agent's identity, instructions, selected model reference, and allowed tool names.
- Define the single-agent runner boundary and normalized runner event vocabulary.
- Adapt assembled Agentle context, model bindings, and tools into the selected external framework.
- Delegate model/tool turn orchestration to that framework rather than implementing a custom loop.
- Translate framework stream events, final output, usage metadata, and failures into Agentle-owned values.

## Non-Responsibilities

- No model endpoint configuration or provider client ownership.
- No context retrieval, history query, memory algorithm, prompt-priority policy, native tool behavior, or subprocess execution.
- No runtime task supervision, event persistence, GUI state, or application shutdown ordering.
- No autonomous agent selection, subagent switching, handoffs, teams, planning graphs, or durable workflows in Phase 1.

## Phase 1 Concepts and Terminology

- **Agent definition:** immutable `id`, display name, instructions, model configuration ID, and ordered allow-list of tool names.
- **Agent runner:** adapter protocol that executes one definition for one run.
- **Run input:** session/run IDs, assembled context, a compatible model binding, tool catalog/invoker, deadline, and cancellation token.
- **Runner event:** backend-neutral stream of text deltas, tool requests/results, usage updates, and final output. Runtime converts these to canonical runtime events.
- **Single-agent orchestration:** the framework-managed cycle of model request, optional tool calls, tool results, and final response for one fixed agent.

## Minimum Public Contracts

- `AgentDefinition` with validated non-empty instructions and tool allow-list.
- `AgentRunInput` containing `AssembledContext`, `ModelBinding`, `ToolCatalog`, `ToolInvoker`, `Deadline`, and `CancellationToken`.
- `AgentRunEvent` variants: `TextDelta`, `ToolRequested`, `ToolStarted`, `ToolCompleted`, `ToolFailed`, `UsageUpdated`, and `FinalOutput`.
- `AgentRunner.run(input) -> AsyncIterator[AgentRunEvent]`, plus asynchronous `close()` and a declared `runner_family`.
- Structured errors: `agent.invalid_definition`, `agent.model_incompatible`, `agent.framework_failure`, `agent.invalid_output`, and `agent.incomplete_stream`.

Runner events contain Agentle tool calls and result values, not Pydantic AI nodes or OpenAI message objects. There must be exactly one `FinalOutput` on successful completion.

## Dependencies

### Permitted internal dependencies

- Foundation control/error contracts.
- Context's assembled output, Models' binding/descriptor, and Tools' catalog/invoker contracts.
- Runtime may depend on Agents; Agents must not depend on Runtime or Persistence.

### Permitted external dependencies

- Pydantic AI in the Phase 1 adapter only.
- No external framework dependency in agent definitions or runner protocols.

## Future Extension Seams

- Add a second runner implementation in Phase 2 and run it through the same contract suite.
- Add explicit compatibility declarations between runner families and model bindings.
- Add handoffs or durable workflows only as new orchestration contracts in Phase 3, not flags on the single-agent runner.
- Agent definitions may gain real versioning when persisted editable definitions exist.

## Phase 0 — Contracts and Boundaries

### Requirements

- [x] Define agent definition, run input, runner event, lifecycle, and error contracts.
- [x] Separate agent behavior from model provider, context assembly, tools, and Runtime supervision.
- [x] Select an adapter-backed framework direction and document its required behavior.
- [x] Record unresolved framework mapping questions in `notes.md`.

### Non-Goals

- No runner implementation, custom agent loop, graph abstraction, or multi-agent API.
- No persistence format for editable agent marketplaces or dynamic discovery.

### Acceptance Criteria

- [x] Runtime can drive a run entirely through `AgentRunner` and Agentle-owned values.
- [x] The runner contract supports streaming, tools, cancellation, deadlines, errors, and shutdown.
- [x] Models, agents, and orchestration have explicitly separate ownership.
- [x] No public type exposes the selected framework.

## Phase 1 — Functional Vertical Path

### Requirements

- [ ] Implement one Pydantic AI runner adapter for one statically selected `AgentDefinition`.
- [ ] Translate `AssembledContext` and stored history into framework messages at the adapter edge.
- [ ] Wrap Agentle `ToolInvoker` calls as framework function tools; the framework must never receive concrete execution backends.
- [ ] Use the framework's all-event streaming API so tool turns finish before final output.
- [ ] Propagate cancellation/deadline to the framework task and wait for its cleanup.
- [ ] Map incomplete streams and framework exceptions to structured errors and close framework resources on shutdown.

### Non-Goals

- No autonomous switching, subagents, handoffs, retries across agents, planning mode, reflection loop, or framework-native persistence/memory.
- No framework-native UI protocol as Agentle's public runtime event contract.

### Acceptance Criteria

- [ ] A fake model can produce text-only and one-tool-call runs through the adapter.
- [ ] Tool allow-lists are enforced before registration with the framework.
- [ ] Cancellation during a model stream and during a tool call terminates without a leaked task.
- [ ] Runner events contain no framework object and end in exactly one final output or structured error.
- [ ] The runner passes the common contract suite without a network connection.

## Later Phases

Phase 2 introduces a second runner to test the contract. Multi-agent handoffs and durable orchestration require separate Phase 3 design; they are not extensions hidden inside Phase 1.

## Related Decisions

- [ADR 0001](../../docs/decisions/0001-static-composition-and-owned-adapters.md)
- [ADR 0003](../../docs/decisions/0003-pydantic-ai-phase-1-adapter.md)
