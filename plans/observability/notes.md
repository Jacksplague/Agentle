# Observability Notes

Use this file for informal research and working material that is not yet an accepted requirement or architectural decision.

## Research

## Candidate Libraries

## Experiments

## Rejected Approaches

## Questions

- Which telemetry beyond the persisted Runtime event journal is required after the vertical path works?
- Should the Phase 1 activity view remain a GUI projection of Runtime events rather than an Observability feature?

## Implementation Observations

- Runtime owns the canonical event schema and Persistence owns durable session/event records. Observability may consume those events for traces/metrics later but must not define a competing event model or journal.
