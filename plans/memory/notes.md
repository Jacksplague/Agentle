# Memory Notes

Use this file for informal research and working material that is not yet an accepted requirement or architectural decision.

## Research

## Candidate Libraries

## Experiments

## Rejected Approaches

## Questions

- Is explicit memory retrieval required anywhere in Phase 1, or is persisted session history sufficient until Phase 2?
- What future retrieval result contract can emit Context contributions without letting Context own ranking or storage?

## Implementation Observations

- The Phase 1 Context plan deliberately accepts retrieved contributions but performs no retrieval. Session transcript loading is Persistence/Runtime behavior, not a Memory algorithm.
