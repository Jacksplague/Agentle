"""Backend-neutral execution contracts used by native tools."""

from dataclasses import dataclass
from typing import Protocol

from agentle.foundation import CancellationToken, Deadline


@dataclass(frozen=True, slots=True)
class FileReadRequest:
    path: str
    start_line: int = 1
    max_lines: int = 200
    max_bytes: int = 65_536

    def __post_init__(self) -> None:
        if not self.path:
            raise ValueError("file path must not be empty")
        if self.start_line < 1:
            raise ValueError("start line must be positive")
        if self.max_lines < 1:
            raise ValueError("line limit must be positive")
        if self.max_bytes < 1:
            raise ValueError("byte limit must be positive")


@dataclass(frozen=True, slots=True)
class FileReadResult:
    text: str
    lines: int
    truncated: bool


@dataclass(frozen=True, slots=True)
class ExecutionControl:
    deadline: Deadline
    cancellation: CancellationToken


class ExecutionBackend(Protocol):
    async def read_text(
        self, request: FileReadRequest, control: ExecutionControl
    ) -> FileReadResult: ...

    async def close(self, grace_seconds: float) -> None: ...
