# Foundation Notes

## Research

- Python 3.12 supplies `typing.Protocol`, `NewType`, timezone-aware `datetime`, and `asyncio` primitives needed by the proposed dependency-light contracts.

## Rejected Approaches

- A shared Pydantic base model for every section would couple internal domain contracts to a validation framework without a Phase 1 need.
- A service locator or component registry would hide dependencies and prematurely resemble plugin infrastructure.
- A generic `Result[T, E]` wrapper is unnecessary while async methods can return typed values and raise section-owned structured exceptions.

## Questions

- Which error `details` keys are safe enough to standardize, rather than leaving them section-owned?

## Implementation Observations

- Redaction must be applied when an exception is converted, not left to each GUI/log consumer.
- Phase 1 implements only explicit `env:` secret references and UUIDv4 opaque IDs. Additional schemes or time-ordered IDs require a concrete consumer.
