import asyncio
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import pytest

from agentle.execution import ExecutionControl, FileReadRequest, LocalExecutionBackend
from agentle.foundation import AgentleError, CancellationSource, Deadline


@dataclass
class ManualClock:
    value: float = 0.0

    def utc_now(self) -> datetime:
        return datetime(2026, 1, 1, tzinfo=UTC)

    def monotonic(self) -> float:
        return self.value


def control(clock: ManualClock, *, seconds: float = 10) -> ExecutionControl:
    return ExecutionControl(
        deadline=Deadline.after(seconds, clock),
        cancellation=CancellationSource().token,
    )


async def test_local_backend_reads_bounded_utf8_lines(tmp_path: Path) -> None:
    (tmp_path / "notes.txt").write_text("one\ntwo\nthree\n", encoding="utf-8")
    clock = ManualClock()
    backend = LocalExecutionBackend(tmp_path, clock=clock)

    result = await backend.read_text(
        FileReadRequest(path="notes.txt", start_line=2, max_lines=1), control(clock)
    )

    assert result.text.replace("\r\n", "\n") == "two\n"
    assert result.lines == 1
    assert result.truncated
    await backend.close(1)


@pytest.mark.parametrize("path", ["../outside.txt", "/absolute.txt", "C:\\absolute.txt"])
async def test_local_backend_rejects_paths_outside_workspace(tmp_path: Path, path: str) -> None:
    clock = ManualClock()
    backend = LocalExecutionBackend(tmp_path, clock=clock)

    with pytest.raises(AgentleError) as caught:
        await backend.read_text(FileReadRequest(path=path), control(clock))

    assert caught.value.info.code == "execution.path_outside_workspace"
    await backend.close(1)


async def test_local_backend_rejects_invalid_utf8(tmp_path: Path) -> None:
    (tmp_path / "binary.bin").write_bytes(b"\xff\xfe")
    clock = ManualClock()
    backend = LocalExecutionBackend(tmp_path, clock=clock)

    with pytest.raises(AgentleError) as caught:
        await backend.read_text(FileReadRequest(path="binary.bin"), control(clock))

    assert caught.value.info.code == "execution.decode"
    await backend.close(1)


async def test_local_backend_honors_byte_limit(tmp_path: Path) -> None:
    (tmp_path / "large.txt").write_text("abcdef", encoding="utf-8")
    clock = ManualClock()
    backend = LocalExecutionBackend(tmp_path, clock=clock)

    result = await backend.read_text(
        FileReadRequest(path="large.txt", max_bytes=3), control(clock)
    )

    assert result.text == "abc"
    assert result.truncated
    await backend.close(1)


async def test_local_backend_honors_preexisting_cancellation_and_deadline(tmp_path: Path) -> None:
    (tmp_path / "notes.txt").write_text("text", encoding="utf-8")
    clock = ManualClock()
    backend = LocalExecutionBackend(tmp_path, clock=clock)
    source = CancellationSource()
    source.cancel()

    with pytest.raises(asyncio.CancelledError):
        await backend.read_text(
            FileReadRequest(path="notes.txt"),
            ExecutionControl(deadline=Deadline.after(1, clock), cancellation=source.token),
        )

    deadline = Deadline.after(0, clock)
    with pytest.raises(AgentleError) as caught:
        await backend.read_text(
            FileReadRequest(path="notes.txt"),
            ExecutionControl(deadline=deadline, cancellation=CancellationSource().token),
        )
    assert caught.value.info.code == "execution.timeout"
    await backend.close(1)


async def test_closed_backend_rejects_new_work(tmp_path: Path) -> None:
    (tmp_path / "notes.txt").write_text("text", encoding="utf-8")
    backend = LocalExecutionBackend(tmp_path)
    await backend.close(1)

    with pytest.raises(AgentleError) as caught:
        await backend.read_text(FileReadRequest(path="notes.txt"), control(ManualClock()))

    assert caught.value.info.code == "execution.unavailable"


async def test_symlink_escape_is_rejected_when_supported(tmp_path: Path) -> None:
    outside = tmp_path.parent / "outside-agentle.txt"
    outside.write_text("outside", encoding="utf-8")
    link = tmp_path / "link.txt"
    try:
        link.symlink_to(outside)
    except OSError:
        pytest.skip("symlinks are unavailable on this platform")
    clock = ManualClock()
    backend = LocalExecutionBackend(tmp_path, clock=clock)

    with pytest.raises(AgentleError) as caught:
        await backend.read_text(FileReadRequest(path="link.txt"), control(clock))

    assert caught.value.info.code == "execution.path_outside_workspace"
    await backend.close(1)
