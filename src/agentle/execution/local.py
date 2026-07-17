"""Trusted local workspace file backend (not a security sandbox)."""

import asyncio
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import cast

from agentle.foundation import AgentleError, Clock, ErrorCategory, ErrorInfo, SystemClock

from .contracts import ExecutionControl, FileReadRequest, FileReadResult


def _execution_error(code: str, message: str) -> AgentleError:
    return AgentleError(ErrorInfo(code=code, category=ErrorCategory.EXECUTION, message=message))


class LocalExecutionBackend:
    """Bounded host filesystem access confined to one canonical workspace."""

    def __init__(self, workspace: str | Path, *, clock: Clock | None = None) -> None:
        try:
            root = Path(workspace).resolve(strict=True)
        except (OSError, RuntimeError) as error:
            raise _execution_error(
                "execution.path_not_found", "The configured workspace does not exist."
            ) from error
        if not root.is_dir():
            raise _execution_error(
                "execution.path_not_found", "The configured workspace is not a directory."
            )
        self._workspace = root
        self._clock = SystemClock() if clock is None else clock
        self._executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="agentle-files")
        self._active: set[asyncio.Task[object]] = set()
        self._closed = False

    @property
    def workspace(self) -> Path:
        return self._workspace

    async def read_text(
        self, request: FileReadRequest, control: ExecutionControl
    ) -> FileReadResult:
        if self._closed:
            raise _execution_error("execution.unavailable", "The execution backend is closed.")
        control.cancellation.raise_if_cancelled()
        remaining = control.deadline.remaining(self._clock)
        if remaining == 0:
            raise _execution_error("execution.timeout", "The file read timed out.")
        current = asyncio.current_task()
        if current is None:
            raise _execution_error("execution.failed", "The file read has no owning task.")
        active_task = cast(asyncio.Task[object], current)
        self._active.add(active_task)
        loop = asyncio.get_running_loop()
        read_future = loop.run_in_executor(self._executor, self._read_sync, request)
        cancellation_wait = asyncio.create_task(control.cancellation.wait())
        waiters = {
            cast(asyncio.Future[object], read_future),
            cast(asyncio.Future[object], cancellation_wait),
        }
        try:
            done, _ = await asyncio.wait(
                waiters,
                timeout=remaining,
                return_when=asyncio.FIRST_COMPLETED,
            )
            if cancellation_wait in done:
                read_future.cancel()
                raise asyncio.CancelledError
            if read_future not in done:
                read_future.cancel()
                raise _execution_error("execution.timeout", "The file read timed out.")
            return read_future.result()
        finally:
            cancellation_wait.cancel()
            await asyncio.gather(cancellation_wait, return_exceptions=True)
            self._active.discard(active_task)

    def _read_sync(self, request: FileReadRequest) -> FileReadResult:
        path = self._resolve_path(request.path)
        try:
            with path.open("rb") as stream:
                data = stream.read(request.max_bytes + 1)
        except FileNotFoundError as error:
            raise _execution_error(
                "execution.path_not_found", "The requested file does not exist."
            ) from error
        except OSError as error:
            raise _execution_error(
                "execution.failed", "The requested file could not be read."
            ) from error
        byte_truncated = len(data) > request.max_bytes
        prefix = data[: request.max_bytes]
        try:
            text = prefix.decode("utf-8")
        except UnicodeDecodeError as error:
            incomplete_suffix = (
                byte_truncated
                and error.end == len(prefix)
                and error.reason == "unexpected end of data"
            )
            if incomplete_suffix:
                text = prefix[: error.start].decode("utf-8")
            else:
                raise _execution_error(
                    "execution.decode", "The requested file is not valid UTF-8 text."
                ) from error
        lines = text.splitlines(keepends=True)
        start_index = request.start_line - 1
        selected = lines[start_index : start_index + request.max_lines]
        line_truncated = start_index > 0 or start_index + request.max_lines < len(lines)
        return FileReadResult(
            text="".join(selected),
            lines=len(selected),
            truncated=byte_truncated or line_truncated,
        )

    def _resolve_path(self, value: str) -> Path:
        requested = Path(value)
        if requested.is_absolute():
            raise _execution_error(
                "execution.path_outside_workspace", "Absolute paths are not allowed."
            )
        lexical = (self._workspace / requested).resolve(strict=False)
        try:
            lexical.relative_to(self._workspace)
        except ValueError as error:
            raise _execution_error(
                "execution.path_outside_workspace", "The requested path leaves the workspace."
            ) from error
        try:
            resolved = (self._workspace / requested).resolve(strict=True)
        except (FileNotFoundError, RuntimeError) as error:
            raise _execution_error(
                "execution.path_not_found", "The requested file does not exist."
            ) from error
        try:
            resolved.relative_to(self._workspace)
        except ValueError as error:
            raise _execution_error(
                "execution.path_outside_workspace", "The requested path leaves the workspace."
            ) from error
        if not resolved.is_file():
            raise _execution_error(
                "execution.path_not_found", "The requested path is not a file."
            )
        return resolved

    async def close(self, grace_seconds: float) -> None:
        if grace_seconds < 0:
            raise ValueError("close grace period cannot be negative")
        if self._closed:
            return
        self._closed = True
        tasks = list(self._active)
        for task in tasks:
            task.cancel()
        if tasks:
            _, pending = await asyncio.wait(tasks, timeout=grace_seconds)
            for task in pending:
                task.cancel()
        await asyncio.to_thread(self._executor.shutdown, wait=True, cancel_futures=True)
