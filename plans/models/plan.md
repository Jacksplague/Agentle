# Models Plan

## Final Vision

Models describes model endpoints and capabilities and opens configured model bindings for agent runners. Provider-specific clients and message formats remain inside adapters, allowing Agentle to replace the Phase 1 OpenAI-compatible implementation without changing runtime, GUI, context, or persistence contracts.

## Responsibilities

- Define model configuration, declared capabilities, identity, and lifecycle.
- Resolve an OpenAI-compatible endpoint into a runner-consumable binding through an Agentle-owned adapter.
- Validate required capability/configuration combinations before a run starts.
- Translate provider setup, authentication, timeout, rate-limit, protocol, and shutdown failures to structured Agentle errors.
- Ensure credentials stay referenced, redacted, and outside persisted configuration snapshots.

## Non-Responsibilities

- No agent instructions, tool loop, agent selection, orchestration, context assembly, retries across complete agent turns, or conversation storage.
- No GUI configuration widgets or direct environment-variable reads in domain code.
- No universal model router, fallback chain, pricing catalog, token budgeter, or provider discovery in Phase 1.
- No provider SDK types in public contracts.

## Phase 1 Concepts and Terminology

- **Provider:** the remote OpenAI-compatible service addressed by a base URL.
- **Model configuration:** immutable values `id`, `model_name`, `base_url`, `api_key_ref`, request timeout, generation settings, and explicit capability overrides.
- **Model capabilities:** booleans for streaming text and function-tool calling; Phase 1 rejects a configuration that lacks either capability.
- **Model adapter:** Agentle-owned protocol that validates configuration and opens a model binding.
- **Model binding:** opaque configured handle with Agentle metadata and an adapter-private backend object. It is compatible only with runner families declared by the adapter.
- **Runner family:** a stable string used to fail clearly when a model binding and agent runner adapter cannot interoperate; it is not a plugin identifier.

## Minimum Public Contracts

- `ModelConfiguration` with a validated HTTPS or explicit localhost base URL, model name, `SecretRef`, request timeout, optional temperature, and output-token limit.
- `ModelCapabilities(streaming_text, function_tools)`.
- `ModelDescriptor(id, display_name, capabilities, runner_family)` for presentation and preflight checks.
- `ModelBinding` protocol exposing only `descriptor` and asynchronous `close()`; its native handle remains adapter-private.
- `ModelAdapter.open(configuration, secret_resolver) -> ModelBinding` and asynchronous `close()`.
- Structured errors: `model.invalid_configuration`, `model.authentication`, `model.rate_limited`, `model.timeout`, `model.protocol`, `model.incompatible_runner`, and `model.unavailable`.

The Phase 1 Pydantic AI/OpenAI adapter may provide a private binding type shared with the Pydantic AI runner adapter inside the infrastructure layer. Core packages never import that type.

## Dependencies

### Permitted internal dependencies

- Foundation identifiers, deadlines, errors, and secret references.
- Agents may consume `ModelBinding`; Models must not import agent definitions or orchestration.

### Permitted external dependencies

- The selected Pydantic AI slim OpenAI integration and its transitive OpenAI client, introduced only during Phase 1 implementation.
- Standard-library URL and lifecycle utilities.

All external model types stay inside `agentle.models.adapters.pydantic_ai_openai` (or an equivalently isolated infrastructure package).

## Future Extension Seams

- Add a second `ModelAdapter` and its contract tests in Phase 2.
- Extend capability data only when an implemented runner or UI needs a capability.
- A router may later choose among descriptors, but `ModelAdapter` is not itself a router or registry.
- Provider-specific settings may live in adapter-owned validated configuration without polluting the common model contract.

## Phase 0 — Contracts and Boundaries

### Requirements

- [x] Define configuration, descriptor, binding, adapter, capability, and error contracts.
- [x] Keep invocation and SDK details behind the model/runner adapter pair.
- [x] State the Phase 1 adapter expectations and replacement boundary.
- [x] Record unresolved endpoint-compatibility questions in `notes.md`.

### Non-Goals

- No provider implementation or production dependency change.
- No routing, fallback, model catalog, benchmarking, or cost dashboard.

### Acceptance Criteria

- [x] Runtime and GUI can identify a model without importing a provider library.
- [x] A runner/model incompatibility has a defined preflight failure.
- [x] The configuration contains a credential reference, never a credential value.
- [x] The Phase 1 external adapter has explicit required behavior and contract-test targets.

## Phase 1 — Functional Vertical Path

### Requirements

- [ ] Add the pinned, minimal Pydantic AI OpenAI optional dependency after a compatibility spike.
- [ ] Implement one OpenAI-compatible adapter using the Chat Completions-compatible model path, custom base URL, model name, resolved API key, request timeout, and generation settings.
- [ ] Validate streaming/tool capability before returning a binding.
- [ ] Map provider exceptions and cancellation without leaking response bodies or secrets.
- [ ] Close the underlying async client during runtime shutdown.

### Non-Goals

- No Responses-API-only features, hosted conversation state, embeddings, multimodal input, provider-native tools, retry router, or second provider.
- No assumption that all OpenAI-compatible endpoints implement identical optional fields.

### Acceptance Criteria

- [ ] Contract tests use a fake transport to verify configuration mapping, streaming, tool-call support, error mapping, cancellation, timeout, and close.
- [ ] One opt-in live smoke test can target a configured compatible endpoint and is excluded from default checks.
- [ ] Replacing the adapter requires no Runtime, GUI, Context, Tool, or Persistence contract change.
- [ ] Tests prove API keys do not appear in descriptors, events, errors, or persisted payloads.

## Later Phases

Phase 2 adds a second adapter to prove the seam. Routing, fallback, richer capabilities, and model catalogs are considered only after two real providers expose concrete differences.

## Related Decisions

- [ADR 0001](../../docs/decisions/0001-static-composition-and-owned-adapters.md)
- [ADR 0003](../../docs/decisions/0003-pydantic-ai-phase-1-adapter.md)

