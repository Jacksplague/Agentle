"""Structured, serializable, and sanitized Agentle errors."""

import asyncio
from dataclasses import dataclass, field
from enum import StrEnum

type ErrorDetail = str | int | float | bool | None


class ErrorCategory(StrEnum):
    CONFIGURATION = "configuration"
    VALIDATION = "validation"
    PROVIDER = "provider"
    TOOL = "tool"
    EXECUTION = "execution"
    PERSISTENCE = "persistence"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"
    INTERNAL = "internal"


@dataclass(frozen=True, slots=True)
class ErrorInfo:
    code: str
    category: ErrorCategory
    message: str
    retryable: bool = False
    details: dict[str, ErrorDetail] = field(default_factory=dict)
    cause_code: str | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "code": self.code,
            "category": self.category.value,
            "message": self.message,
            "retryable": self.retryable,
            "details": dict(self.details),
            "cause_code": self.cause_code,
        }


class AgentleError(Exception):
    """Expected boundary failure with a safe public representation."""

    def __init__(self, info: ErrorInfo) -> None:
        super().__init__(info.message)
        self.info = info


def redact_text(value: str, sensitive_values: tuple[str, ...]) -> str:
    redacted = value
    for sensitive in sensitive_values:
        if sensitive:
            redacted = redacted.replace(sensitive, "[REDACTED]")
    return redacted


def _redact_info(info: ErrorInfo, sensitive_values: tuple[str, ...]) -> ErrorInfo:
    details: dict[str, ErrorDetail] = {}
    for key, value in info.details.items():
        details[key] = redact_text(value, sensitive_values) if isinstance(value, str) else value
    return ErrorInfo(
        code=info.code,
        category=info.category,
        message=redact_text(info.message, sensitive_values),
        retryable=info.retryable,
        details=details,
        cause_code=info.cause_code,
    )


def error_info_from_exception(
    error: BaseException, *, sensitive_values: tuple[str, ...] = ()
) -> ErrorInfo:
    """Convert an exception without leaking unknown exception text."""

    if isinstance(error, AgentleError):
        return _redact_info(error.info, sensitive_values)
    if isinstance(error, asyncio.CancelledError):
        return ErrorInfo(
            code="operation.cancelled",
            category=ErrorCategory.CANCELLED,
            message="The operation was cancelled.",
        )
    if isinstance(error, TimeoutError):
        return ErrorInfo(
            code="operation.timeout",
            category=ErrorCategory.TIMEOUT,
            message="The operation timed out.",
            retryable=True,
        )
    return ErrorInfo(
        code="internal.unexpected",
        category=ErrorCategory.INTERNAL,
        message="An unexpected internal error occurred.",
    )
