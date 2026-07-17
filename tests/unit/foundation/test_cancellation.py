import asyncio

import pytest

from agentle.foundation import CancellationSource


async def test_cancellation_source_wakes_waiters_and_raises() -> None:
    source = CancellationSource()
    waiter = asyncio.create_task(source.token.wait())

    assert not source.token.cancelled
    source.cancel()
    await asyncio.wait_for(waiter, timeout=0.1)

    assert source.token.cancelled
    with pytest.raises(asyncio.CancelledError):
        source.token.raise_if_cancelled()
