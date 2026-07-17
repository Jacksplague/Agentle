"""Bounded in-process publication of already-committed runtime events."""

import asyncio

from agentle.foundation import AgentleError, ErrorCategory, ErrorInfo

from .events import RuntimeEvent


class EventSubscription:
    def __init__(self, capacity: int) -> None:
        self._queue: asyncio.Queue[RuntimeEvent] = asyncio.Queue(maxsize=capacity)
        self._closed_error: ErrorInfo | None = None

    async def get(self) -> RuntimeEvent:
        if self._closed_error is not None and self._queue.empty():
            raise AgentleError(self._closed_error)
        return await self._queue.get()

    def close(self) -> None:
        if self._closed_error is None:
            self._closed_error = ErrorInfo(
                code="runtime.subscription_closed",
                category=ErrorCategory.INTERNAL,
                message="The runtime event subscription is closed.",
            )

    def _offer(self, event: RuntimeEvent) -> bool:
        if self._closed_error is not None:
            return False
        try:
            self._queue.put_nowait(event)
        except asyncio.QueueFull:
            self._closed_error = ErrorInfo(
                code="runtime.subscriber_slow",
                category=ErrorCategory.INTERNAL,
                message="The event subscriber fell behind and must replay persisted events.",
                retryable=True,
            )
            return False
        return True


class EventPublisher:
    """Publish in order without allowing subscribers to block a run."""

    def __init__(self, subscriber_capacity: int = 256) -> None:
        if subscriber_capacity < 1:
            raise ValueError("subscriber capacity must be positive")
        self._subscriber_capacity = subscriber_capacity
        self._subscriptions: list[EventSubscription] = []

    def subscribe(self) -> EventSubscription:
        subscription = EventSubscription(self._subscriber_capacity)
        self._subscriptions.append(subscription)
        return subscription

    def publish(self, event: RuntimeEvent) -> None:
        self._subscriptions = [
            subscription
            for subscription in self._subscriptions
            if subscription._offer(event)
        ]

    def close(self) -> None:
        for subscription in self._subscriptions:
            subscription.close()
        self._subscriptions.clear()
