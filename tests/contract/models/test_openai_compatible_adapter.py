import json
from collections.abc import AsyncIterator
from pathlib import Path

import httpx
import pytest
from openai import AsyncOpenAI

from agentle.agents import (
    AgentDefinition,
    AgentRunEvent,
    AgentRunInput,
    FinalOutput,
    TextDelta,
    ToolCompleted,
    ToolRequested,
)
from agentle.agents.adapters import PydanticAISingleAgentRunner
from agentle.context import AssembledContext
from agentle.foundation import (
    AgentleError,
    CancellationSource,
    Deadline,
    EnvironmentSecretResolver,
    SecretRef,
    SystemClock,
    new_run_id,
    new_session_id,
)
from agentle.models import ModelConfiguration
from agentle.models.adapters import OpenAICompatibleModelAdapter
from agentle.tools import (
    SideEffect,
    ToolCall,
    ToolCatalog,
    ToolDefinition,
    ToolInvocationContext,
    ToolInvoker,
    ToolResult,
)


class RecordingTool:
    def __init__(self) -> None:
        self.calls: list[ToolCall] = []
        self._definition = ToolDefinition(
            name="read_text",
            description="Read text.",
            input_schema={
                "type": "object",
                "additionalProperties": False,
                "properties": {"path": {"type": "string"}},
                "required": ["path"],
            },
            side_effect=SideEffect.READ_ONLY,
        )

    @property
    def definition(self) -> ToolDefinition:
        return self._definition

    async def invoke(
        self, call: ToolCall, context: ToolInvocationContext
    ) -> ToolResult:
        self.calls.append(call)
        return ToolResult("contents", "text/plain", False, {})


def sse(*chunks: dict[str, object]) -> bytes:
    records = [f"data: {json.dumps(chunk)}\n\n" for chunk in chunks]
    records.append("data: [DONE]\n\n")
    return "".join(records).encode()


async def collect(stream: AsyncIterator[AgentRunEvent]) -> list[AgentRunEvent]:
    return [event async for event in stream]


async def test_fake_transport_streams_one_tool_turn_and_closes_client(
    tmp_path: Path,
) -> None:
    requests: list[dict[str, object]] = []
    api_key = "secret-value-that-must-not-leak"

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url == "https://models.example.test/v1/chat/completions"
        assert request.headers["authorization"] == f"Bearer {api_key}"
        body = json.loads(request.content)
        assert isinstance(body, dict)
        requests.append(body)
        base = {
            "id": f"chatcmpl-{len(requests)}",
            "object": "chat.completion.chunk",
            "created": 1,
            "model": "test-model",
        }
        if len(requests) == 1:
            chunks = (
                {
                    **base,
                    "choices": [
                        {
                            "index": 0,
                            "delta": {
                                "role": "assistant",
                                "tool_calls": [
                                    {
                                        "index": 0,
                                        "id": "call-1",
                                        "type": "function",
                                        "function": {
                                            "name": "read_text",
                                            "arguments": '{"path":"README.md"}',
                                        },
                                    }
                                ],
                            },
                            "finish_reason": None,
                        }
                    ],
                },
                {
                    **base,
                    "choices": [
                        {"index": 0, "delta": {}, "finish_reason": "tool_calls"}
                    ],
                },
            )
        else:
            chunks = (
                {
                    **base,
                    "choices": [
                        {
                            "index": 0,
                            "delta": {"role": "assistant", "content": "done"},
                            "finish_reason": None,
                        }
                    ],
                },
                {
                    **base,
                    "choices": [
                        {"index": 0, "delta": {}, "finish_reason": "stop"}
                    ],
                },
            )
        return httpx.Response(
            200,
            headers={"content-type": "text/event-stream"},
            content=sse(*chunks),
        )

    http_client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    client = AsyncOpenAI(
        api_key=api_key,
        base_url="https://models.example.test/v1",
        http_client=http_client,
        max_retries=0,
    )
    adapter = OpenAICompatibleModelAdapter(lambda _configuration, _key: client)
    binding = await adapter.open(
        ModelConfiguration(
            model_id="default-model",
            model_name="test-model",
            base_url="https://models.example.test/v1",
            api_key_ref=SecretRef.parse("env:TEST_API_KEY"),
            request_timeout_seconds=2,
            temperature=0.2,
            max_output_tokens=100,
        ),
        EnvironmentSecretResolver({"TEST_API_KEY": api_key}),
    )
    tool = RecordingTool()
    invoker = ToolInvoker(ToolCatalog([tool]), ["read_text"])
    cancellation = CancellationSource()
    clock = SystemClock()
    run_input = AgentRunInput(
        session_id=new_session_id(),
        run_id=new_run_id(),
        definition=AgentDefinition(
            "default", "Default", "Be helpful.", "default-model", ("read_text",)
        ),
        context=AssembledContext(
            instructions=("Be helpful.",),
            messages=(),
            current_request="Read README.md",
            provenance=(),
            fingerprint="test",
        ),
        model=binding,
        tool_invoker=invoker,
        workspace=str(tmp_path),
        deadline=Deadline.after(5, clock),
        cancellation=cancellation.token,
    )

    events = await collect(PydanticAISingleAgentRunner().run(run_input))

    assert len(requests) == 2
    assert tool.calls[0].arguments == {"path": "README.md"}
    assert any(isinstance(event, ToolRequested) for event in events)
    assert any(isinstance(event, ToolCompleted) for event in events)
    assert any(isinstance(event, TextDelta) and event.text == "done" for event in events)
    assert isinstance(events[-1], FinalOutput)
    assert events[-1].output == "done"
    assert api_key not in repr(binding.descriptor)

    await adapter.close()
    assert client.is_closed


@pytest.mark.parametrize(
    ("failure", "expected_code"),
    [("authentication", "model.authentication"), ("timeout", "model.timeout")],
)
async def test_provider_failures_are_structured_and_redacted(
    tmp_path: Path, failure: str, expected_code: str
) -> None:
    api_key = "never-show-this-api-key"

    def handler(request: httpx.Request) -> httpx.Response:
        if failure == "timeout":
            raise httpx.ReadTimeout(f"timed out with {api_key}", request=request)
        return httpx.Response(
            401,
            request=request,
            json={"error": {"message": f"invalid {api_key}"}},
        )

    client = AsyncOpenAI(
        api_key=api_key,
        base_url="https://models.example.test/v1",
        http_client=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
        max_retries=0,
    )
    adapter = OpenAICompatibleModelAdapter(lambda _configuration, _key: client)
    binding = await adapter.open(
        ModelConfiguration(
            "model",
            "test-model",
            "https://models.example.test/v1",
            SecretRef.parse("env:API_KEY"),
            0.1,
        ),
        EnvironmentSecretResolver({"API_KEY": api_key}),
    )
    cancellation = CancellationSource()
    clock = SystemClock()
    run_input = AgentRunInput(
        session_id=new_session_id(),
        run_id=new_run_id(),
        definition=AgentDefinition("agent", "Agent", "Instructions", "model", ()),
        context=AssembledContext(
            instructions=("Instructions",),
            messages=(),
            current_request="hello",
            provenance=(),
            fingerprint="test",
        ),
        model=binding,
        tool_invoker=ToolInvoker(ToolCatalog([]), []),
        workspace=str(tmp_path),
        deadline=Deadline.after(1, clock),
        cancellation=cancellation.token,
    )

    with pytest.raises(AgentleError) as captured:
        await collect(PydanticAISingleAgentRunner().run(run_input))

    assert captured.value.info.code == expected_code
    assert api_key not in repr(captured.value.info)
    await adapter.close()
