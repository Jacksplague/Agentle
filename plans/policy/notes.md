# Policy Notes

Use this file for informal research and working material that is not yet an accepted requirement or architectural decision.

## Research

## Candidate Libraries

## Experiments

## Rejected Approaches

## Questions

- What Phase 1 contract binds an approval to the exact executable argv, canonical working directory, environment additions, and expiry?
- Does read-only workspace access require an explicit decision, or is workspace confinement plus tool enablement the initial allow rule?
- Which Runtime command/event pair requests and records human approval without coupling Policy to PyQt?

## Implementation Observations

- The first read-only `read_text` slice can proceed without subprocess authority. `run_command` remains blocked until these Policy questions are resolved and its Phase 0 plan is completed.
