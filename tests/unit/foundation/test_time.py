from dataclasses import dataclass
from datetime import UTC, datetime, timedelta, timezone

import pytest

from agentle.foundation import Deadline, as_utc


@dataclass
class ManualClock:
    monotonic_value: float = 10.0

    def utc_now(self) -> datetime:
        return datetime(2026, 1, 1, tzinfo=UTC) + timedelta(seconds=self.monotonic_value)

    def monotonic(self) -> float:
        return self.monotonic_value


def test_as_utc_rejects_naive_datetime() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        as_utc(datetime(2026, 1, 1))


def test_as_utc_normalizes_an_aware_datetime() -> None:
    value = datetime(2026, 1, 1, 4, tzinfo=timezone(timedelta(hours=4)))

    assert as_utc(value) == datetime(2026, 1, 1, tzinfo=UTC)


def test_deadline_uses_monotonic_time_and_only_shortens() -> None:
    clock = ManualClock()
    deadline = Deadline.after(10, clock)

    clock.monotonic_value = 13
    assert deadline.remaining(clock) == 7
    assert deadline.shorten(3, clock).expires_at == 16
    assert deadline.shorten(30, clock) == deadline

    clock.monotonic_value = 20
    assert deadline.expired(clock)
    assert deadline.remaining(clock) == 0
