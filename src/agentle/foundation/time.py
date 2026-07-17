"""UTC and monotonic time contracts."""

from dataclasses import dataclass
from datetime import UTC, datetime
from time import monotonic
from typing import Protocol


class Clock(Protocol):
    """Clock boundary used by lifecycle code and deterministic tests."""

    def utc_now(self) -> datetime: ...

    def monotonic(self) -> float: ...


class SystemClock:
    """Production wall and monotonic clock."""

    def utc_now(self) -> datetime:
        return datetime.now(UTC)

    def monotonic(self) -> float:
        return monotonic()


def as_utc(value: datetime) -> datetime:
    """Validate an aware datetime and normalize it to UTC."""

    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("timestamp must be timezone-aware")
    return value.astimezone(UTC)


@dataclass(frozen=True, slots=True)
class Deadline:
    """An absolute monotonic deadline."""

    expires_at: float

    @classmethod
    def after(cls, seconds: float, clock: Clock) -> "Deadline":
        if seconds < 0:
            raise ValueError("deadline duration must be non-negative")
        return cls(expires_at=clock.monotonic() + seconds)

    def remaining(self, clock: Clock) -> float:
        return max(0.0, self.expires_at - clock.monotonic())

    def expired(self, clock: Clock) -> bool:
        return self.remaining(clock) == 0.0

    def shorten(self, seconds: float, clock: Clock) -> "Deadline":
        candidate = Deadline.after(seconds, clock)
        return Deadline(expires_at=min(self.expires_at, candidate.expires_at))
