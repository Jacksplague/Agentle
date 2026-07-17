# Agentle Architecture

## Purpose

Agentle is a modular application host, not a replacement for every agent framework, memory engine, model router, tool protocol, or sandbox implementation.

Agentle owns the desktop experience, application lifecycle, configuration, normalized events, project state, permission policy, and adapter contracts. External systems remain behind narrow Agentle-owned adapters and are assembled explicitly at the application entry point.

## Core principles

1. Build one working vertical path before broadening the platform.
2. Define contracts at responsibility boundaries, not around specific libraries.
3. Keep external frameworks behind adapters.
4. Add an abstraction only when a second implementation or clear boundary justifies it.
5. Keep the GUI independent from provider SDKs and execution details.
6. Normalize runtime events so the UI and persistence layers are backend-agnostic.
7. Make cancellation, timeouts, error propagation, and clean shutdown first-class behavior.
8. Preserve provenance for context, memory, tool activity, and execution results.
9. Prefer contract tests over architecture-preserving boilerplate.
10. Avoid giant plugin systems until external extension requirements are real.

## Dependency direction

```text
GUI / CLI
    |
    v
Application and Runtime Services
    |
    v
Domain Contracts and Policies
    |
    v
Adapters and Infrastructure
    |
    v
External Libraries and Services
```

Core modules must not import GUI classes or concrete third-party backend implementations.

The Phase 1 composition root is the only place that constructs concrete adapters. Dependencies are passed explicitly; there is no global persistence service, provider registry, service locator, or dynamic discovery.

## Stable responsibility boundaries

- **Foundation** defines dependency-light identifiers, errors, deadlines, cancellation, clocks, and secret references.
- **Runtime** owns lifecycle, commands, events, streaming, cancellation, task management, and shutdown.
- **Projects** owns project metadata, workspace configuration, selected components, and portable project state.
- **Models** owns model configuration, capabilities, and provider bindings, not agent behavior or routing.
- **Agents** owns agent definitions and adapters to external reasoning/orchestration systems.
- **Context** deterministically assembles already-retrieved contributions; it does not retrieve them.
- **Memory** stores and retrieves structured memory records; retrieval results may become Context contributions.
- **Tools** exposes callable action definitions and invocation; tools are not skills or execution backends.
- **Skills** provides procedural knowledge and tool requirements; skills are not callable.
- **Execution** performs typed filesystem/process operations; the local backend is not a security sandbox.
- **Persistence** explicitly stores sessions, transcript messages, runs, and normalized events behind repositories.
- **GUI** submits application commands and consumes normalized events.
- **Observability** consumes activity for traces and metrics; Runtime owns event schemas and Persistence owns the session journal.
- **Policy** decides whether an operation is allowed, denied, constrained, or requires approval.
- **Integrations** coordinates only cross-cutting external interoperability; section-specific adapters remain with Models, Agents, Tools, Execution, or Persistence.

## Phase policy

- **Phase 0:** contracts, boundaries, and acceptance criteria
- **Phase 1:** one functional vertical path
- **Phase 2:** second implementations that prove modularity
- **Phase 3:** advanced agent behavior and durable workflows
- **Phase 4:** plugin ecosystem, remote execution, and broader distribution

## Initial technology direction

Candidate technologies remain decisions rather than hard dependencies until validated:

- Python 3.12+
- PyQt6 for the desktop GUI
- Pydantic for typed data and configuration
- Pydantic AI or another adapter-backed agent runtime
- OpenAI-compatible model access for Phase 1
- SQLite for local sessions, events, and minimal memory
- MCP for external tool integration after the native vertical path works

## Phase 1 vertical-path contracts

```text
PyQt widgets
  -> QtRuntimeClient (commands only)
  -> Runtime coordinator (normalized, durable events)
  -> ContextAssembler + AgentRunner
  -> private Pydantic AI runner/model adapter pair
  -> ToolInvoker -> read_text -> LocalExecutionBackend
  -> explicit SQLite repositories
```

The GUI never imports or invokes the runner, provider SDK, repositories, tools, execution backend, filesystem APIs, or subprocess APIs. Runtime persists a normalized event before publishing it. The first implementation slice uses a read-only tool; local subprocess support remains a later Phase 1 item gated by completion of the Policy authorization contract.

See `docs/decisions/` and each section's `notes.md` for research and unresolved choices.
