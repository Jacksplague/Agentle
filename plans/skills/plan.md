# Skills Plan

## Final Vision

Describe the intended final functionality and user-visible outcome for this section.

## Responsibilities

- Define what this section owns.
- Keep responsibilities narrow enough to remain testable and replaceable.

## Non-Responsibilities

- List adjacent concerns that belong to other sections.
- Record boundaries explicitly to prevent coupling.

## Core Concepts

Define the terminology, entities, states, and workflows used by this section.

## Public Contracts

List protocols, commands, events, schemas, services, and data models exposed to other sections.

## Dependencies

List permitted dependencies on other internal sections and external libraries.

## Extension Points

Identify the narrow seams where additional providers, backends, or modules may be added later.

## Phase 0 — Contracts and Boundaries

### Requirements

- [ ] Define section responsibilities and non-responsibilities.
- [ ] Define only the contracts required by Phase 1.
- [ ] Record unresolved architectural decisions.

### Non-Goals

- No speculative plugin framework.
- No implementation unrelated to the Phase 1 vertical path.

### Acceptance Criteria

- [ ] Dependencies and public contracts are documented.
- [ ] Phase 1 requirements are testable.
- [ ] Cross-section ownership conflicts are resolved or recorded.

## Phase 1 — Functional Vertical Path

### Requirements

- [ ] Define the smallest implementation needed for the first end-to-end workflow.

### Non-Goals

- No second backend unless required to validate a contract.
- No advanced management UI or ecosystem features.

### Acceptance Criteria

- [ ] The Phase 1 implementation participates in the working vertical path.
- [ ] Errors, cancellation, and shutdown behavior are defined where applicable.
- [ ] Tests cover the public behavior introduced in this phase.

## Phase 2 — Prove Modularity

### Requirements

- [ ] Add a second implementation or integration where applicable.
- [ ] Refine contracts based on real compatibility needs.

### Acceptance Criteria

- [ ] Both implementations pass the same contract tests.
- [ ] Backend selection does not require a major rewrite.

## Phase 3 — Advanced Capability

### Requirements

- [ ] Add advanced workflows and operational features relevant to this section.

### Acceptance Criteria

- [ ] Advanced behavior remains observable, cancellable, and testable.

## Phase 4 — Ecosystem and External Extension

### Requirements

- [ ] Support external extension, distribution, or remote integration where appropriate.

### Acceptance Criteria

- [ ] Compatibility and version requirements are explicit.

## Open Design Decisions

- [ ] Add section-specific decisions here.

## Initial Phase 1 Focus

- Filesystem skill package
- Markdown instructions plus a small manifest
- Manual skill assignment to an agent or project
- No automatic skill discovery or selection
