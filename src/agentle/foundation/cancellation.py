"""Cooperative cancellation primitives."""

import asyncio
from typing import Protocol


class CancellationToken(Protocol):
    """Read-only cancellation view passed to downstream operations."""

    @property
    def cancelled(self) -> bool: ...

    async def wait(self) -> None: ...

    def raise_if_cancelled(self) -> None: ...


class CancellationSource:
    """Cancellation owner whose read-only surface satisfies ``CancellationToken``."""

    def __init__(self) -> None:
        self._event = asyncio.Event()

    @property
    def token(self) -> CancellationToken:
        return self

    @property
    def cancelled(self) -> bool:
        return self._event.is_set()

    def cancel(self) -> None:
        self._event.set()

    async def wait(self) -> None:
        await self._event.wait()

    def raise_if_cancelled(self) -> None:
        if self.cancelled:
            raise asyncio.CancelledError
