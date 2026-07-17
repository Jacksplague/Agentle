"""Deterministic, side-effect-free Phase 1 context assembly."""

import hashlib
import json

from agentle.foundation import AgentleError, ErrorCategory, ErrorInfo

from .contracts import (
    AssembledContext,
    AssembledMessage,
    ContextContribution,
    ContextPriority,
    ContextRequest,
    ContributionKind,
    ProvenanceRecord,
)

_EXPECTED_PRIORITY = {
    ContributionKind.APPLICATION_INSTRUCTIONS: ContextPriority.APPLICATION,
    ContributionKind.AGENT_INSTRUCTIONS: ContextPriority.AGENT,
    ContributionKind.HISTORY: ContextPriority.HISTORY,
    ContributionKind.CURRENT_REQUEST: ContextPriority.REQUEST,
}


def _context_error(code: str, message: str) -> AgentleError:
    return AgentleError(ErrorInfo(code=code, category=ErrorCategory.VALIDATION, message=message))


class ContextAssembler:
    def assemble(self, request: ContextRequest) -> AssembledContext:
        if request.character_limit < 1:
            raise _context_error("context.limit_exceeded", "The context limit must be positive.")
        if sum(len(item.content) for item in request.contributions) > request.character_limit:
            raise _context_error(
                "context.limit_exceeded", "The assembled context exceeds the configured limit."
            )
        for item in request.contributions:
            if item.priority is not _EXPECTED_PRIORITY[item.kind]:
                raise _context_error(
                    "context.invalid_order", "A context contribution has an invalid priority."
                )
            if not item.source.strip() or not item.source_id.strip():
                raise _context_error(
                    "context.invalid_order", "Every contribution requires source provenance."
                )

        requests = [
            item
            for item in request.contributions
            if item.kind is ContributionKind.CURRENT_REQUEST
        ]
        if len(requests) != 1 or not requests[0].content.strip():
            raise _context_error(
                "context.missing_request", "Exactly one non-empty current request is required."
            )

        instructions = sorted(
            (
                item
                for item in request.contributions
                if item.kind
                in {
                    ContributionKind.APPLICATION_INSTRUCTIONS,
                    ContributionKind.AGENT_INSTRUCTIONS,
                }
            ),
            key=lambda item: (item.priority, item.source, item.source_id),
        )
        history = [
            item for item in request.contributions if item.kind is ContributionKind.HISTORY
        ]
        if any(item.role is None or item.occurred_at is None for item in history):
            raise _context_error(
                "context.invalid_role", "History requires a user/assistant role and timestamp."
            )
        history.sort(key=lambda item: (item.occurred_at, item.source_id))
        ordered = [*instructions, *history, requests[0]]
        fingerprint_data = [self._fingerprint_item(item) for item in ordered]
        fingerprint = hashlib.sha256(
            json.dumps(
                fingerprint_data,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            ).encode()
        ).hexdigest()
        return AssembledContext(
            instructions=tuple(item.content for item in instructions),
            messages=tuple(
                AssembledMessage(
                    role=item.role,
                    content=item.content,
                    provenance_refs=(item.provenance_ref,),
                )
                for item in history
                if item.role is not None
            ),
            current_request=requests[0].content,
            provenance=tuple(
                ProvenanceRecord(
                    reference=item.provenance_ref,
                    kind=item.kind,
                    occurred_at=item.occurred_at,
                )
                for item in ordered
            ),
            fingerprint=fingerprint,
        )

    @staticmethod
    def _fingerprint_item(item: ContextContribution) -> dict[str, object]:
        return {
            "kind": item.kind.value,
            "content": item.content,
            "source": item.source,
            "source_id": item.source_id,
            "priority": int(item.priority),
            "role": None if item.role is None else item.role.value,
            "occurred_at": None if item.occurred_at is None else item.occurred_at.isoformat(),
        }
