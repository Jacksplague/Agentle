import os
from pathlib import Path

import pytest

from agentle.agents import AgentDefinition, AgentRunInput, FinalOutput
from agentle.agents.adapters import PydanticAISingleAgentRunner
from agentle.context import AssembledContext
from agentle.foundation import (
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
from agentle.tools import ToolCatalog, ToolInvoker

pytestmark = pytest.mark.live


async def test_configured_openai_compatible_endpoint(tmp_path: Path) -> None:
    base_url = os.environ.get("AGENTLE_MODEL_BASE_URL")
    model_name = os.environ.get("AGENTLE_MODEL_NAME")
    api_key = os.environ.get("AGENTLE_MODEL_API_KEY")
    if not base_url or not model_name or api_key is None:
        pytest.skip("configure AGENTLE_MODEL_BASE_URL, AGENTLE_MODEL_NAME, and API key")

    adapter = OpenAICompatibleModelAdapter()
    binding = await adapter.open(
        ModelConfiguration(
            "live-model",
            model_name,
            base_url,
            SecretRef.parse("env:AGENTLE_MODEL_API_KEY"),
            30,
            max_output_tokens=64,
        ),
        EnvironmentSecretResolver(os.environ),
    )
    source = CancellationSource()
    clock = SystemClock()
    run_input = AgentRunInput(
        session_id=new_session_id(),
        run_id=new_run_id(),
        definition=AgentDefinition(
            "live-agent", "Live agent", "Answer briefly.", "live-model", ()
        ),
        context=AssembledContext(
            instructions=("Answer briefly.",),
            messages=(),
            current_request="Reply with the single word OK.",
            provenance=(),
            fingerprint="live",
        ),
        model=binding,
        tool_invoker=ToolInvoker(ToolCatalog([]), []),
        workspace=str(tmp_path),
        deadline=Deadline.after(30, clock),
        cancellation=source.token,
    )
    try:
        events = [
            event async for event in PydanticAISingleAgentRunner().run(run_input)
        ]
        assert isinstance(events[-1], FinalOutput)
        assert events[-1].output.strip()
    finally:
        await adapter.close()
