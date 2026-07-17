"""Static Phase 1 application composition root."""

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from agentle.agents import AgentDefinition
from agentle.agents.adapters import PydanticAISingleAgentRunner
from agentle.context import ContextAssembler
from agentle.execution import LocalExecutionBackend
from agentle.foundation import EnvironmentSecretResolver, SecretRef, SystemClock
from agentle.models import ModelConfiguration
from agentle.models.adapters import OpenAICompatibleModelAdapter
from agentle.persistence import SQLitePersistence
from agentle.runtime import RuntimeFactory, RuntimeService
from agentle.tools import ReadTextTool, ToolCatalog, ToolInvoker


@dataclass(frozen=True, slots=True)
class AppConfiguration:
    workspace: Path
    database_path: Path
    model: ModelConfiguration

    @classmethod
    def from_environment(
        cls, environment: Mapping[str, str], *, current_directory: Path
    ) -> "AppConfiguration":
        workspace = Path(environment.get("AGENTLE_WORKSPACE", current_directory)).resolve()
        data_directory = Path(
            environment.get("AGENTLE_DATA_DIR", workspace / ".agentle")
        ).resolve()
        model_name = environment.get("AGENTLE_MODEL_NAME", "").strip()
        if not model_name:
            raise ValueError("AGENTLE_MODEL_NAME must be configured")
        return cls(
            workspace=workspace,
            database_path=data_directory / "agentle.sqlite3",
            model=ModelConfiguration(
                model_id="default-model",
                model_name=model_name,
                base_url=environment.get(
                    "AGENTLE_MODEL_BASE_URL", "http://localhost:1234/v1"
                ),
                api_key_ref=SecretRef.parse("env:AGENTLE_MODEL_API_KEY"),
                request_timeout_seconds=120,
                max_output_tokens=4_096,
            ),
        )


def runtime_factory(
    configuration: AppConfiguration, environment: Mapping[str, str]
) -> RuntimeFactory:
    async def build() -> RuntimeService:
        if not configuration.workspace.is_dir():
            raise ValueError("the configured workspace does not exist")
        configuration.database_path.parent.mkdir(parents=True, exist_ok=True)
        clock = SystemClock()
        persistence = await SQLitePersistence.open(configuration.database_path)
        backend = LocalExecutionBackend(configuration.workspace, clock=clock)
        model_adapter = OpenAICompatibleModelAdapter()
        try:
            model = await model_adapter.open(
                configuration.model, EnvironmentSecretResolver(environment)
            )
        except Exception:
            await backend.close(1)
            await persistence.close()
            await model_adapter.close()
            raise

        async def close_model_adapter(_grace_seconds: float) -> None:
            await model_adapter.close()

        invoker = ToolInvoker(ToolCatalog([ReadTextTool(backend)]), ["read_text"])
        runtime = RuntimeService(
            persistence=persistence,
            context_assembler=ContextAssembler(),
            runner=PydanticAISingleAgentRunner(),
            model=model,
            tool_invoker=invoker,
            agent=AgentDefinition(
                agent_id="default",
                display_name="Agentle",
                instructions="Help the user with their workspace using the allowed tools.",
                model_id=configuration.model.model_id,
                allowed_tools=("read_text",),
            ),
            clock=clock,
            application_instructions="You are the Agentle desktop assistant.",
            workspace=str(configuration.workspace),
            shutdown_callbacks=(backend.close, close_model_adapter),
        )
        await runtime.recover_interrupted_runs()
        return runtime

    return build
