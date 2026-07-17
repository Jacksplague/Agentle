# Context Notes

## Research

- Phase 1 can remain provider-neutral by assembling instructions and chat roles while the runner adapter handles external message types.

## Rejected Approaches

- Letting Context query Memory or Persistence conflates retrieval with assembly and makes deterministic unit tests harder.
- Provider tokenization and automatic compression are premature before a target context limit and real transcripts exist.
- Rendering provenance into the prompt by default would spend tokens and may expose internal paths/IDs.

## Questions

- Should assistant tool activity appear in assembled history, or should Phase 1 send only user/assistant transcript messages while the framework handles tool turns within a run?
- Is the fingerprint required in persisted run metadata in Phase 1, or only events/tests?

## Implementation Observations

- Memory retrieval is not part of the first slice. When added, its output is a contribution and its ranking remains a Memory responsibility.
- Runtime defaults the assembled context limit to 100,000 characters. The runner passes ordered instruction blocks to Pydantic AI and keeps provider-specific system-message normalization at that adapter edge.
