# Context Plan

## Final Vision

Context deterministically assembles already-available instructions and conversation material into a provider-neutral input for an agent run. Every contribution retains source and priority metadata so later memory, skill, and project sources can be added without merging retrieval algorithms into prompt assembly.

## Responsibilities

- Accept explicit context contributions from Runtime and order them by documented Phase 1 rules.
- Validate roles, provenance, priority, and size and produce one immutable `AssembledContext`.
- Preserve session-message identity and source metadata for diagnostics.
- Keep assembly deterministic for the same request and inputs.
- Report invalid or over-limit inputs before the model adapter is invoked.

## Non-Responsibilities

- No querying SQLite, files, vector stores, memory providers, skill directories, or model endpoints.
- No memory extraction, storage, ranking, or retrieval; Memory owns those responsibilities.
- No agent orchestration, provider-specific tokenization, automatic summarization, compression, or prompt optimization in Phase 1.
- No tool execution, permission decisions, or GUI transcript formatting.

## Phase 1 Concepts and Terminology

- **Contribution:** a typed piece of input with `source`, `source_id`, `kind`, `priority`, content, and optional original timestamp.
- **Source:** the producer of a contribution, such as application instructions, agent definition, persisted session history, or current user request.
- **Priority:** conflict/ordering class, not a claim of trust. Phase 1 order is application instructions, agent instructions, chronological session history, current request.
- **Provenance:** metadata identifying where content came from; it remains Agentle metadata and is not automatically sent to the model as text.
- **Assembled context:** ordered provider-neutral instructions and chat messages plus provenance metadata and a deterministic fingerprint.
- **Retrieval:** selecting candidate records from a source. Retrieval happens before assembly and is outside this section.

## Minimum Public Contracts

- `ContextContribution(kind, content, source, source_id, priority, occurred_at)`.
- `ContextRequest(session_id, run_id, contributions, character_limit)`.
- `AssembledMessage(role, content, provenance_refs)` with Phase 1 roles `user` and `assistant`.
- `AssembledContext(instructions, messages, current_request, provenance, fingerprint)`.
- `ContextAssembler.assemble(request) -> AssembledContext`.
- Structured errors: `context.invalid_role`, `context.missing_request`, `context.invalid_order`, and `context.limit_exceeded`.

The fingerprint is for repeatability and diagnostics, not a cache key or security digest.

## Dependencies

### Permitted internal dependencies

- Foundation IDs and structured errors.
- Runtime supplies contributions; Agents consume the assembled result. Context imports neither section's service implementation.

### Permitted external dependencies

- Python standard library only in Phase 1.

Context must not import persistence adapters, memory libraries, skill loaders, provider SDKs, tokenizers, or PyQt.

## Future Extension Seams

- Memory retrieval, skills, and project sources may each produce `ContextContribution` values through explicit application wiring.
- A token-budget strategy may replace the simple character limit after a real provider need is measured.
- Compression may be an explicitly injected pre-assembly service later; it is not built into retrieval or the base assembler.
- New contribution kinds require ordering and provenance rules plus tests.

## Phase 0 — Contracts and Boundaries

### Requirements

- [x] Define contribution, provenance, deterministic ordering, assembled output, and error contracts.
- [x] Separate retrieval from assembly and explicitly exclude Phase 1 memory retrieval.
- [x] Define the minimum inputs for application/agent instructions, session history, and current request.
- [x] Record unresolved size and provider-message questions in `notes.md`.

### Non-Goals

- No assembler implementation, retrieval provider, skill parsing, memory algorithm, compression, or token budgeting.
- No generic prompt-template language or context plugin chain.

### Acceptance Criteria

- [x] Identical ordered inputs must have an identical specified result and fingerprint.
- [x] Every output element can be traced to one or more input contributions.
- [x] Persistence and Memory are not dependencies of `ContextAssembler`.
- [x] The Phase 1 ordering and overflow behavior are testable without a model.

## Phase 1 — Functional Vertical Path

### Requirements

- [x] Implement a deterministic assembler for application instructions, one agent definition, persisted session history, and the current user request.
- [x] Reject empty current requests, invalid history roles, and inputs above a configured character limit.
- [x] Preserve message IDs/timestamps as provenance while keeping provider formatting in the agent adapter.
- [x] Compute a stable fingerprint over normalized content and provenance IDs.

### Non-Goals

- No memory provider call, skill auto-selection, RAG, summarization, truncation heuristic, token counting, or provider-specific prompt caching.
- No transmission of provenance metadata to a model unless explicitly rendered by a future policy.

### Acceptance Criteria

- [x] Unit tests cover ordering, role validation, provenance, repeatability, empty input, and overflow.
- [x] A multi-turn persisted transcript becomes the expected provider-neutral message order.
- [x] The assembler performs no I/O and has no hidden mutable state.
- [x] Memory retrieval can later produce contributions without changing assembly ownership.

## Later Phases

Phase 2 may integrate an explicit memory retriever as a contribution producer. Token budgeting and compression wait for measured context pressure; they remain separate from retrieval.

## Related Decisions

- [ADR 0001](../../docs/decisions/0001-static-composition-and-owned-adapters.md)
