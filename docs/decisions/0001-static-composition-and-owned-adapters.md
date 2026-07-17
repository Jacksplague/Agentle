# ADR 0001: Use static composition and Agentle-owned adapters

- **Status:** Accepted
- **Date:** 2026-07-17
- **Owners:** Agentle maintainers

## Context

The vertical path crosses PyQt, an agent framework, an OpenAI-compatible provider, native tools, local execution, and SQLite. External libraries are valuable, but allowing their types or lifecycle to cross section boundaries would couple the application to one stack. Dynamic discovery is not required in Phase 1.

## Decision

- Construct the Phase 1 object graph explicitly in one application composition root.
- Pass dependencies through constructors; persistence, providers, tools, and backends are never ambient globals.
- Define narrow Agentle-owned protocols and typed data at responsibility boundaries.
- Keep external imports in adapter/infrastructure modules. Translate configuration, values, events, errors, cancellation, and close behavior at each adapter edge.
- Permit paired infrastructure adapters (for example a Pydantic AI runner and model binding) to share private types. Core/public contracts expose only Agentle values and explicit compatibility metadata.
- Add a second implementation by explicit composition after the first path works. Do not add dynamic plugin discovery in Phase 1.

## Consequences

- GUI, Runtime, Context, Tools, and Persistence remain independent of provider/framework APIs.
- Tests can supply fakes without booting external systems.
- Adapter code performs deliberate mapping and may need updates when a library changes.
- A framework cannot silently become Agentle's public architecture.

## Alternatives considered

- **Use framework types end to end:** less mapping initially, but makes replacement and backend-independent persistence/UI impractical.
- **Build model/agent/tool orchestration ourselves:** conflicts with the requirement to integrate proven systems.
- **Create a plugin/service registry now:** adds lifecycle/version/discovery work without a Phase 1 consumer.

