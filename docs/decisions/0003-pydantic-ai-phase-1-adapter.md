# ADR 0003: Use Pydantic AI behind paired Phase 1 agent/model adapters

- **Status:** Accepted
- **Date:** 2026-07-17
- **Owners:** Agentle maintainers

## Context

Phase 1 needs one async single-agent model/tool loop, all-event streaming, typed function tools, message history, and an OpenAI-compatible endpoint. Agentle must use a proven agentic system without letting that system define public contracts.

Pydantic AI's official documentation describes OpenAI-compatible provider configuration, function tools, serializable message history, and streaming of model/tool events. Its version is evolving, so the implementation must be pinned and contract-tested rather than treated as permanent architecture.

## Decision

- Use the minimal Pydantic AI OpenAI integration for the Phase 1 compatibility spike and implementation.
- Target the OpenAI-compatible Chat Completions path for the broadest first-endpoint compatibility; exclude Responses-only features.
- Implement a Pydantic AI `AgentRunner` adapter and compatible model adapter/binding as a private pair under ADR 0001.
- Delegate the agent/tool loop to Pydantic AI. Agentle supplies assembled context and wraps `ToolInvoker`; it does not build a second loop around model calls.
- Translate all framework events, messages, usage, and exceptions into Agentle contracts. Do not use framework-native UI, persistence, memory, durable execution, subagents, or plugin features in Phase 1.
- Before adding a production dependency, pin a version that passes fake-transport contract tests for streaming, a tool turn, cancellation, timeout, error mapping, and close.

## Consequences

- Agentle benefits from a proven orchestration/provider integration while retaining a replacement boundary.
- The paired adapters have private coupling, made visible through an explicit runner-family compatibility check.
- Framework upgrades are deliberate dependency work and may require adapter mapping changes.
- This decision does not select Pydantic AI for future memory, GUI, persistence, sandboxing, or multi-agent architecture.

## Phase 1 implementation record

- The compatibility spike passed on 2026-07-17 with `pydantic-ai-slim[openai]==1.107.1` and `openai==2.46.0`; both are pinned because Agentle directly constructs the OpenAI client and maps the framework's v1 all-event surface.
- The adapter disables framework retries and parallel tool calls for deterministic first-slice behavior. Runtime owns the outer deadline and cancellation policy.
- Offline tests cover Chat Completions SSE text, one function-tool turn, authentication, timeout, cancellation during model/tool activity, client close, and credential redaction.
- Upgrading to Pydantic AI 2.x is replacement-boundary work and must rerun these contract tests; it is not an automatic dependency update.

## Alternatives considered

- **OpenAI Agents SDK:** credible, but the initial architecture already identifies a provider-neutral Pydantic direction and Pydantic AI directly documents the required OpenAI-compatible/tool/history surfaces. It remains a candidate for the Phase 2 second runner.
- **Direct OpenAI SDK plus custom loop:** would reimplement agent orchestration.
- **Framework types as public contracts:** rejected by ADR 0001.

## References

- [Pydantic AI agents and all-event streaming](https://pydantic.dev/docs/ai/core-concepts/agent/)
- [Pydantic AI OpenAI and compatible-provider configuration](https://pydantic.dev/docs/ai/models/openai/)
- [Pydantic AI function tools](https://pydantic.dev/docs/ai/tools-toolsets/tools/)
- [Pydantic AI message history](https://pydantic.dev/docs/ai/core-concepts/message-history/)
