# Models Notes

## Research

- Pydantic AI documents configurable OpenAI providers/clients, OpenAI-compatible APIs, all-event streaming, function tools, and serializable message history. These cover the Phase 1 adapter expectations while remaining external-library behavior that Agentle must normalize.
- The OpenAI-compatible ecosystem is not uniform: Chat Completions is the conservative Phase 1 compatibility target; Responses-specific features stay excluded.

## Candidate Libraries

- `pydantic-ai-slim` with its OpenAI optional extra is the accepted Phase 1 candidate, subject to a pinned compatibility spike before adding it to `pyproject.toml`.

## Rejected Approaches

- A hand-written HTTP/OpenAI protocol client would reimplement provider behavior and error handling.
- A multi-provider router is unnecessary with one configured endpoint.
- Exposing the framework's model object as an Agentle public contract would make replacement invasive.

## Questions

- Which exact Pydantic AI version and OpenAI client combination passes the Phase 1 contract suite at implementation time?
- Should capability support be configured explicitly only, or may the adapter perform a guarded endpoint probe?
- Which optional generation fields are safe across the first target endpoint beyond temperature and maximum output tokens?
- Which local/live OpenAI-compatible endpoint will be the documented development smoke-test target?

## Implementation Observations

- The model binding and runner adapter are a paired infrastructure implementation; compatibility must fail during preflight rather than by downcast deep inside a run.

