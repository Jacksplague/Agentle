from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import pytest

from agentle.execution import LocalExecutionBackend
from agentle.foundation import (
    AgentleError,
    CancellationSource,
    Deadline,
    RunId,
    SessionId,
    ToolCallId,
)
from agentle.tools import (
    ReadTextTool,
    ToolCall,
    ToolCatalog,
    ToolInvocationContext,
    ToolInvoker,
)


@dataclass
class ManualClock:
    value: float = 0.0

    def utc_now(self) -> datetime:
        return datetime(2026, 1, 1, tzinfo=UTC)

    def monotonic(self) -> float:
        return self.value


def invocation_context(workspace: Path, clock: ManualClock) -> ToolInvocationContext:
    return ToolInvocationContext(
        session_id=SessionId("session"),
        run_id=RunId("run"),
        workspace=str(workspace),
        deadline=Deadline.after(10, clock),
        cancellation=CancellationSource().token,
    )


async def test_read_text_flows_through_static_catalog_and_backend(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text("Agentle\n", encoding="utf-8")
    clock = ManualClock()
    backend = LocalExecutionBackend(tmp_path, clock=clock)
    invoker = ToolInvoker(ToolCatalog([ReadTextTool(backend)]), ["read_text"])

    result = await invoker.invoke(
        ToolCall(
            call_id=ToolCallId("call"),
            name="read_text",
            arguments={"path": "README.md"},
        ),
        invocation_context(tmp_path, clock),
    )

    assert [definition.name for definition in invoker.definitions] == ["read_text"]
    assert result.content.replace("\r\n", "\n") == "Agentle\n"
    assert result.metadata == {"lines": 1}
    await backend.close(1)


@pytest.mark.parametrize(
    "arguments",
    [
        {},
        {"path": 123},
        {"path": "README.md", "max_lines": True},
        {"path": "README.md", "unknown": "value"},
    ],
)
async def test_read_text_rejects_invalid_arguments(
    tmp_path: Path, arguments: dict[str, object]
) -> None:
    clock = ManualClock()
    backend = LocalExecutionBackend(tmp_path, clock=clock)
    invoker = ToolInvoker(ToolCatalog([ReadTextTool(backend)]), ["read_text"])

    with pytest.raises(AgentleError) as caught:
        await invoker.invoke(
            ToolCall(  # type: ignore[arg-type]
                call_id=ToolCallId("call"),
                name="read_text",
                arguments=arguments,
            ),
            invocation_context(tmp_path, clock),
        )

    assert caught.value.info.code == "tool.invalid_arguments"
    await backend.close(1)


async def test_invoker_distinguishes_unknown_and_disallowed_tools(tmp_path: Path) -> None:
    clock = ManualClock()
    backend = LocalExecutionBackend(tmp_path, clock=clock)
    catalog = ToolCatalog([ReadTextTool(backend)])
    invoker = ToolInvoker(catalog, [])
    context = invocation_context(tmp_path, clock)

    with pytest.raises(AgentleError) as disallowed:
        await invoker.invoke(
            ToolCall(call_id=ToolCallId("call"), name="read_text", arguments={"path": "x"}),
            context,
        )
    with pytest.raises(AgentleError) as unknown:
        await invoker.invoke(
            ToolCall(call_id=ToolCallId("call"), name="missing", arguments={}), context
        )

    assert disallowed.value.info.code == "tool.not_allowed"
    assert unknown.value.info.code == "tool.unknown"
    await backend.close(1)
