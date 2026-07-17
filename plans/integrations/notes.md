# Integrations Notes

Use this file for informal research and working material that is not yet an accepted requirement or architectural decision.

## Research

## Candidate Libraries

## Experiments

## Rejected Approaches

## Questions

- Does a future integration span multiple ownership sections, or should it be an adapter owned directly by Models, Agents, Tools, Execution, or Persistence?
- Is an Integrations section still justified once MCP is treated as a Tools adapter and model providers remain Models adapters?

## Implementation Observations

- No Integration contract is required by the first vertical path. The Pydantic AI and OpenAI-compatible adapters stay in Agents/Models; future MCP remains a Tools concern unless a real cross-cutting responsibility appears.
