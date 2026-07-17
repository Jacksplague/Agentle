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

- Which Pydantic AI all-event API is most stable in the pinned implementation version?
- Does Phase 1 disable parallel tool calls for deterministic event ordering, or normalize concurrent calls with independent call IDs?
- What usage fields can be normalized consistently without promising provider-specific accounting?
- How should framework retries inside one run be surfaced without making a retry policy part of Runtime?

## Implementation Observations

- The adapter must retain framework-native message history only at its edge; SQLite stores Agentle transcript/events rather than pickled or opaque framework objects.

