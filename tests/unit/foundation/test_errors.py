import asyncio

from agentle.foundation import (
    AgentleError,
    ErrorCategory,
    ErrorInfo,
    error_info_from_exception,
)


def test_expected_error_is_structured_and_redacted() -> None:
    secret = "super-secret-key"
    error = AgentleError(
        ErrorInfo(
            code="provider.authentication",
            category=ErrorCategory.PROVIDER,
            message=f"Provider rejected {secret}",
            details={"response": f"credential={secret}"},
        )
    )

    info = error_info_from_exception(error, sensitive_values=(secret,))

    assert info.message == "Provider rejected [REDACTED]"
    assert info.details == {"response": "credential=[REDACTED]"}
    assert secret not in str(info.to_dict())


def test_unknown_exception_text_is_not_exposed() -> None:
    secret = "secret-in-unknown-exception"

    info = error_info_from_exception(RuntimeError(secret))

    assert info.code == "internal.unexpected"
    assert secret not in str(info.to_dict())


def test_cancellation_and_timeout_have_stable_categories() -> None:
    cancelled = error_info_from_exception(asyncio.CancelledError())
    timed_out = error_info_from_exception(TimeoutError())

    assert cancelled.category is ErrorCategory.CANCELLED
    assert timed_out.category is ErrorCategory.TIMEOUT
    assert timed_out.retryable
