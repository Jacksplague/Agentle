import asyncio
import json
from pathlib import Path

import httpx
import pytest
from openai import AsyncOpenAI

from agentle.agents import AgentDefinition
from agentle.agents.adapters import PydanticAISingleAgentRunner
from agentle.context import ContextAssembler
from agentle.execution import LocalExecutionBackend
from agentle.foundation import EnvironmentSecretResolver, SecretRef, SystemClock
from agentle.models import ModelConfiguration
from agentle.models.adapters import OpenAICompatibleModelAdapter
from agentle.persistence import SQLitePersistence
from agentle.runtime import (
    CommandStatus,
    CreateSession,
    EventKind,
    RuntimeEvent,
    RuntimeService,
    Shutdown,
    SubmitPrompt,
)
from agentle.tools import ReadTextTool, ToolCatalog, ToolInvoker

pytestmark = pytest.mark.integration


def sse(*chunks: dict[str, object]) -> bytes:
    values = [f"data: {json.dumps(chunk)}\n\n" for chunk in chunks]
    values.append("data: [DONE]\n\n")
    return "".join(values).encode()


async def next_kind(subscription, kind: EventKind) -> RuntimeEvent:  # type: ignore[no-untyped-def]
    while True:
        event = await asyncio.wait_for(subscription.get(), timeout=2)
        if event.kind is kind:
            return event


async def test_full_offline_vertical_path_reads_file_and_replays_journal(
    tmp_path: Path,
) -> None:
    (tmp_path / "note.txt").write_text("hello from workspace", encoding="utf-8")
    request_count = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal request_count
        request_count += 1
        base = {
            "id": f"chatcmpl-{request_count}",
            "object": "chat.completion.chunk",
            "created": 1,
            "model": "test-model",
        }
        if request_count == 1:
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
                                            "arguments": '{"path":"note.txt"}',
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
            body = json.loads(request.content)
            assert "hello from workspace" in json.dumps(body)
            chunks = (
                {
                    **base,
                    "choices": [
                        {
                            "index": 0,
                            "delta": {
                                "role": "assistant",
                                "content": "The file says hello.",
                            },
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

    api_key = "vertical-path-secret"
    client = AsyncOpenAI(
        api_key=api_key,
        base_url="https://models.example.test/v1",
        http_client=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
        max_retries=0,
    )
    model_adapter = OpenAICompatibleModelAdapter(lambda _config, _key: client)
    model = await model_adapter.open(
        ModelConfiguration(
            "model",
            "test-model",
            "https://models.example.test/v1",
            SecretRef.parse("env:API_KEY"),
            2,
        ),
        EnvironmentSecretResolver({"API_KEY": api_key}),
    )
    clock = SystemClock()
    persistence = await SQLitePersistence.open(tmp_path / "agentle.sqlite3")
    backend = LocalExecutionBackend(tmp_path, clock=clock)
    invoker = ToolInvoker(ToolCatalog([ReadTextTool(backend)]), ["read_text"])
    runtime = RuntimeService(
        persistence=persistence,
        context_assembler=ContextAssembler(),
        runner=PydanticAISingleAgentRunner(),
        model=model,
        tool_invoker=invoker,
        agent=AgentDefinition(
            "default", "Agentle", "Read files when asked.", "model", ("read_text",)
        ),
        clock=clock,
        application_instructions="You are Agentle.",
        workspace=str(tmp_path),
        shutdown_callbacks=(backend.close,),
    )
    subscription = runtime.subscribe()
    receipt = await runtime.submit(CreateSession(title="Vertical"))
    assert receipt.status is CommandStatus.ACCEPTED
    created = await next_kind(subscription, EventKind.SESSION_CREATED)
    receipt = await runtime.submit(
        SubmitPrompt(
            session_id=created.session_id,
            text="Read note.txt",
            agent_id="default",
            timeout_seconds=5,
        )
    )
    assert receipt.status is CommandStatus.ACCEPTED
    completed = await next_kind(subscription, EventKind.RUN_COMPLETED)

    snapshot = await runtime.load_session(created.session_id)
    assert completed.payload["output"] == "The file says hello."
    assert [event.sequence for event in snapshot.events] == list(
        range(1, len(snapshot.events) + 1)
    )
    assert [message.content for message in snapshot.messages] == [
        "Read note.txt",
        "The file says hello.",
    ]
    assert {event.kind for event in snapshot.events} >= {
        EventKind.TOOL_REQUESTED,
        EventKind.TOOL_STARTED,
        EventKind.TOOL_COMPLETED,
        EventKind.RUN_COMPLETED,
    }
    assert api_key not in json.dumps([event.payload for event in snapshot.events])

    await runtime.submit(Shutdown(grace_seconds=1))
    await model_adapter.close()
    assert client.is_closed
