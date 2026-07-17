"""Pydantic AI/OpenAI-compatible Chat Completions model adapter."""

from collections.abc import Awaitable, Callable
from typing import Any, cast

from openai import AsyncOpenAI
from pydantic_ai.models import Model
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai.settings import ModelSettings

from agentle.foundation import (
    AgentleError,
    ErrorCategory,
    ErrorInfo,
    SecretResolver,
)
from agentle.models.contracts import (
    PYDANTIC_AI_RUNNER_FAMILY,
    ModelCapabilities,
    ModelConfiguration,
    ModelDescriptor,
)

type _ClientFactory = Callable[[ModelConfiguration, str], AsyncOpenAI]


class _PydanticAIModelBinding:
    """Adapter-private model handle shared only with the paired runner."""

    def __init__(
        self,
        *,
        descriptor: ModelDescriptor,
        native_model: Model,
        model_settings: ModelSettings,
        close_callback: Callable[[], Awaitable[None]],
    ) -> None:
        self._descriptor = descriptor
        self.native_model = native_model
        self.model_settings = model_settings
        self._close_callback = close_callback
        self._closed = False

    @property
    def descriptor(self) -> ModelDescriptor:
        return self._descriptor

    async def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        await self._close_callback()


def _default_client_factory(configuration: ModelConfiguration, api_key: str) -> AsyncOpenAI:
    return AsyncOpenAI(
        api_key=api_key,
        base_url=configuration.base_url,
        timeout=configuration.request_timeout_seconds,
        max_retries=0,
    )


class OpenAICompatibleModelAdapter:
    """Open one explicitly configured Pydantic AI Chat Completions binding."""

    runner_family = PYDANTIC_AI_RUNNER_FAMILY

    def __init__(self, client_factory: _ClientFactory | None = None) -> None:
        self._client_factory = client_factory or _default_client_factory
        self._bindings: list[_PydanticAIModelBinding] = []
        self._closed = False

    async def open(
        self, configuration: ModelConfiguration, secret_resolver: SecretResolver
    ) -> _PydanticAIModelBinding:
        if self._closed:
            raise AgentleError(
                ErrorInfo(
                    code="model.adapter_closed",
                    category=ErrorCategory.CONFIGURATION,
                    message="The model adapter is closed.",
                )
            )
        api_key = secret_resolver.resolve(configuration.api_key_ref)
        client: AsyncOpenAI | None = None
        try:
            client = self._client_factory(configuration, api_key)
            provider = OpenAIProvider(openai_client=client)
            native_model = OpenAIChatModel(
                cast(Any, configuration.model_name),
                provider=provider,
            )
            settings = ModelSettings(
                timeout=configuration.request_timeout_seconds,
                parallel_tool_calls=False,
            )
            if configuration.temperature is not None:
                settings["temperature"] = configuration.temperature
            if configuration.max_output_tokens is not None:
                settings["max_tokens"] = configuration.max_output_tokens
        except Exception as error:
            if client is not None:
                await client.close()
            raise AgentleError(
                ErrorInfo(
                    code="model.invalid_configuration",
                    category=ErrorCategory.CONFIGURATION,
                    message="The OpenAI-compatible model configuration is invalid.",
                )
            ) from error

        binding = _PydanticAIModelBinding(
            descriptor=ModelDescriptor(
                model_id=configuration.model_id,
                display_name=configuration.model_name,
                capabilities=ModelCapabilities(streaming_text=True, function_tools=True),
                runner_family=self.runner_family,
            ),
            native_model=native_model,
            model_settings=settings,
            close_callback=client.close,
        )
        self._bindings.append(binding)
        return binding

    async def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        for binding in self._bindings:
            await binding.close()
        self._bindings.clear()
