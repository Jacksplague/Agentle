"""Thread-safe owner for an asyncio RuntimeService instance."""

import asyncio
import threading
from collections.abc import Awaitable, Callable
from concurrent.futures import Future

from agentle.foundation import ErrorInfo, SessionId, error_info_from_exception

from .commands import CommandReceipt, CommandStatus, RuntimeCommand, Shutdown
from .events import RuntimeEvent
from .publisher import EventSubscription
from .service import RuntimeService, SessionSnapshot

type RuntimeFactory = Callable[[], Awaitable[RuntimeService]]


class RuntimeThreadClient:
    """Own one RuntimeService and its event loop in a dedicated thread."""

    def __init__(
        self,
        factory: RuntimeFactory,
        *,
        on_ready: Callable[[], None],
        on_receipt: Callable[[CommandReceipt], None],
        on_event: Callable[[RuntimeEvent], None],
        on_snapshot: Callable[[SessionSnapshot], None],
        on_error: Callable[[ErrorInfo], None],
        on_stopped: Callable[[], None],
    ) -> None:
        self._factory = factory
        self._on_ready = on_ready
        self._on_receipt = on_receipt
        self._on_event = on_event
        self._on_snapshot = on_snapshot
        self._on_error = on_error
        self._on_stopped = on_stopped
        self._thread: threading.Thread | None = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._service: RuntimeService | None = None
        self._stop_event: asyncio.Event | None = None
        self._state_lock = threading.Lock()

    @property
    def alive(self) -> bool:
        thread = self._thread
        return thread is not None and thread.is_alive()

    def start(self) -> None:
        with self._state_lock:
            if self._thread is not None:
                raise RuntimeError("the runtime thread has already been started")
            self._thread = threading.Thread(
                target=self._thread_main,
                name="agentle-runtime",
                daemon=False,
            )
            self._thread.start()

    def submit(self, command: RuntimeCommand) -> Future[None]:
        loop = self._require_loop()
        return asyncio.run_coroutine_threadsafe(self._submit(command), loop)

    def load_session(self, session_id: SessionId) -> Future[None]:
        loop = self._require_loop()
        return asyncio.run_coroutine_threadsafe(self._load_session(session_id), loop)

    def join(self, timeout: float | None = None) -> bool:
        thread = self._thread
        if thread is None:
            return True
        thread.join(timeout)
        return not thread.is_alive()

    def _require_loop(self) -> asyncio.AbstractEventLoop:
        with self._state_lock:
            loop = self._loop
        if loop is None or loop.is_closed():
            raise RuntimeError("the runtime thread is not ready")
        return loop

    def _thread_main(self) -> None:
        try:
            asyncio.run(self._main())
        except BaseException as error:
            if isinstance(error, (KeyboardInterrupt, SystemExit)):
                raise
            self._on_error(error_info_from_exception(error))
        finally:
            with self._state_lock:
                self._loop = None
                self._service = None
                self._stop_event = None
            self._on_stopped()

    async def _main(self) -> None:
        loop = asyncio.get_running_loop()
        service = await self._factory()
        subscription = service.subscribe()
        stop_event = asyncio.Event()
        with self._state_lock:
            self._loop = loop
            self._service = service
            self._stop_event = stop_event
        event_task = asyncio.create_task(self._forward_events(subscription))
        self._on_ready()
        await stop_event.wait()
        event_task.cancel()
        await asyncio.gather(event_task, return_exceptions=True)

    async def _forward_events(self, subscription: EventSubscription) -> None:
        while True:
            self._on_event(await subscription.get())

    async def _submit(self, command: RuntimeCommand) -> None:
        service = self._service
        if service is None:
            raise RuntimeError("the runtime service is unavailable")
        try:
            receipt = await service.submit(command)
            self._on_receipt(receipt)
            if isinstance(command, Shutdown) and receipt.status is CommandStatus.ACCEPTED:
                stop_event = self._stop_event
                if stop_event is not None:
                    stop_event.set()
        except BaseException as error:
            if isinstance(error, (KeyboardInterrupt, SystemExit)):
                raise
            self._on_error(error_info_from_exception(error))

    async def _load_session(self, session_id: SessionId) -> None:
        service = self._service
        if service is None:
            raise RuntimeError("the runtime service is unavailable")
        try:
            self._on_snapshot(await service.load_session(session_id))
        except Exception as error:
            self._on_error(error_info_from_exception(error))
