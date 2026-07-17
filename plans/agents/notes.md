# Agents Notes

## Research

- Pydantic AI's all-event streaming APIs expose text and tool lifecycle activity through an async interface and run the agent graph to completion. Agentle still needs its own stable event mapping.

## Candidate Libraries

- Pydantic AI is selected for the Phase 1 runner adapter because it supplies the single-agent model/tool loop, typed tools, async streaming, and OpenAI-compatible model integration needed by the vertical path.

## Rejected Approaches

- A custom `while tool_calls` orchestration loop would duplicate framework behavior.
- Framework graph/node types are too detailed and unstable to become Runtime events.
- Autonomous agent routing is explicitly outside Phase 1.

## Questions

- Should later adapters expose cached/reasoning token detail after a second provider proves a portable vocabulary?
- If framework retries are enabled later, which normalized event indicates them without making Runtime own provider retry policy?

## Implementation Observations

- The adapter must retain framework-native message history only at its edge; SQLite stores Agentle transcript/events rather than pickled or opaque framework objects.
- Phase 1 uses `run_stream_events()`, disables parallel tool calls and framework retries, and normalizes only aggregate input/output token usage.
- `Tool.from_schema` preserves Agentle's JSON Schema while callbacks receive only a run-scoped `ToolInvoker` and Agentle control values.
