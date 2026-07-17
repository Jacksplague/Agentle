import asyncio
from collections.abc import AsyncIterator
from pathlib import Path

import pytest
from pydantic_ai.messages import ModelMessage
from pydantic_ai.models.function import AgentInfo, DeltaToolCall, FunctionModel
from pydantic_ai.settings import ModelSettings

from agentle.agents import (
    AgentDefinition,
    AgentRunEvent,
    AgentRunInput,
    FinalOutput,
    ToolCompleted,
    ToolFailed,
    ToolRequested,
    ToolStarted,
)
from agentle.agents.adapters import PydanticAISingleAgentRunner
from agentle.context import AssembledContext
from agentle.foundation import (
    AgentleError,
    CancellationSource,
    Deadline,
    ErrorCategory,
    ErrorInfo,
    SystemClock,
    new_run_id,
    new_session_id,
)
from agentle.models import (
    PYDANTIC_AI_RUNNER_FAMILY,
    ModelCapabilities,
    ModelDescriptor,
)
from agentle.models.adapters.pydantic_ai_openai import _PydanticAIModelBinding
from agentle.tools import (
    SideEffect,
    ToolCall,
    ToolCatalog,
    ToolDefinition,
    ToolInvocationContext,
    ToolInvoker,
    ToolResult,
)


class ScriptedTool:
    def __init__(
        self,
        error: ErrorInfo | None = None,
        entered: asyncio.Event | None = None,
    ) -> None:
        self.error = error
        self.entered = entered
        self._definition = ToolDefinition(
            "read_text",
            "Read text.",
            {
                "type": "object",
                "properties": {"path": {"type": "string"}},
                "required": ["path"],
                "additionalProperties": False,
            },
            SideEffect.READ_ONLY,
        )

    @property
    def definition(self) -> ToolDefinition:
        return self._definition

    async def invoke(
        self, call: ToolCall, context: ToolInvocationContext
    ) -> ToolResult:
        if self.entered is not None:
            self.entered.set()
            await asyncio.Event().wait()
        if self.error is not None:
            raise AgentleError(self.error)
        return ToolResult("contents", "text/plain", True, {})


async def no_op() -> None:
    return None


def run_input(
    model: FunctionModel,
    tool: ScriptedTool,
    tmp_path: Path,
    cancellation: CancellationSource | None = None,
) -> AgentRunInput:
    source = cancellation or CancellationSource()
    binding = _PydanticAIModelBinding(
        descriptor=ModelDescriptor(
            "model",
            "Model",
            ModelCapabilities(True, True),
            PYDANTIC_AI_RUNNER_FAMILY,
        ),
        native_model=model,
        model_settings=ModelSettings(parallel_tool_calls=False),
        close_callback=no_op,
    )
    return AgentRunInput(
        session_id=new_session_id(),
        run_id=new_run_id(),
        definition=AgentDefinition(
            "agent", "Agent", "Instructions", "model", ("read_text",)
        ),
        context=AssembledContext(
            instructions=("Instructions",),
            messages=(),
            current_request="Read the file",
            provenance=(),
            fingerprint="test",
        ),
        model=binding,
        tool_invoker=ToolInvoker(ToolCatalog([tool]), ["read_text"]),
        workspace=str(tmp_path),
        deadline=Deadline.after(5, SystemClock()),
        cancellation=source.token,
    )


async def collect(stream: AsyncIterator[AgentRunEvent]) -> list[AgentRunEvent]:
    return [event async for event in stream]


async def test_runner_normalizes_successful_and_failed_tool_results(tmp_path: Path) -> None:
    async def stream(
        messages: list[ModelMessage], info: AgentInfo
    ) -> AsyncIterator[str | dict[int, DeltaToolCall]]:
        if len(messages) == 1:
            yield {
                0: DeltaToolCall(
                    "read_text", '{"path":"README.md"}', tool_call_id="call-1"
                )
            }
        else:
            yield "done"

    success = await collect(
        PydanticAISingleAgentRunner().run(
            run_input(FunctionModel(stream_function=stream), ScriptedTool(), tmp_path)
        )
    )
    assert [type(event) for event in success if not isinstance(event, FinalOutput)][:3] == [
        ToolRequested,
        ToolStarted,
        ToolCompleted,
    ]
    assert isinstance(success[-1], FinalOutput)

    failure = ErrorInfo("tool.denied", ErrorCategory.TOOL, "Denied")
    failed = await collect(
        PydanticAISingleAgentRunner().run(
            run_input(
                FunctionModel(stream_function=stream),
                ScriptedTool(failure),
                tmp_path,
            )
        )
    )
    failed_event = next(event for event in failed if isinstance(event, ToolFailed))
    assert failed_event.error == failure
    assert isinstance(failed[-1], FinalOutput)


async def test_runner_propagates_cancellation_and_closes(tmp_path: Path) -> None:
    entered = asyncio.Event()

    async def stream(
        messages: list[ModelMessage], info: AgentInfo
    ) -> AsyncIterator[str | dict[int, DeltaToolCall]]:
        entered.set()
        await asyncio.Event().wait()
        yield "unreachable"

    runner = PydanticAISingleAgentRunner()
    task = asyncio.create_task(
        collect(
            runner.run(
                run_input(FunctionModel(stream_function=stream), ScriptedTool(), tmp_path)
            )
        )
    )
    await asyncio.wait_for(entered.wait(), timeout=1)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task

    await runner.close()
    with pytest.raises(AgentleError) as captured:
        await collect(
            runner.run(
                run_input(FunctionModel(stream_function=stream), ScriptedTool(), tmp_path)
            )
        )
    assert captured.value.info.code == "agent.runner_closed"


async def test_runner_cancels_while_native_tool_is_active(tmp_path: Path) -> None:
    entered = asyncio.Event()

    async def stream(
        messages: list[ModelMessage], info: AgentInfo
    ) -> AsyncIterator[str | dict[int, DeltaToolCall]]:
        if len(messages) == 1:
            yield {
                0: DeltaToolCall(
                    "read_text", '{"path":"README.md"}', tool_call_id="call-1"
                )
            }
        else:
            yield "unreachable"

    task = asyncio.create_task(
        collect(
            PydanticAISingleAgentRunner().run(
                run_input(
                    FunctionModel(stream_function=stream),
                    ScriptedTool(entered=entered),
                    tmp_path,
                )
            )
        )
    )
    await asyncio.wait_for(entered.wait(), timeout=1)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
