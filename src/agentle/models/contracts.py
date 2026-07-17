"""Provider-neutral model configuration and binding contracts."""

from dataclasses import dataclass
from typing import Protocol
from urllib.parse import urlsplit

from agentle.foundation import SecretRef, SecretResolver

PYDANTIC_AI_RUNNER_FAMILY = "pydantic-ai-v1"


@dataclass(frozen=True, slots=True)
class ModelCapabilities:
    streaming_text: bool
    function_tools: bool


@dataclass(frozen=True, slots=True)
class ModelConfiguration:
    model_id: str
    model_name: str
    base_url: str
    api_key_ref: SecretRef
    request_timeout_seconds: float
    temperature: float | None = None
    max_output_tokens: int | None = None

    def __post_init__(self) -> None:
        if not self.model_id.strip() or not self.model_name.strip():
            raise ValueError("model identifiers must not be empty")
        if self.request_timeout_seconds <= 0:
            raise ValueError("model request timeout must be positive")
        if self.max_output_tokens is not None and self.max_output_tokens < 1:
            raise ValueError("maximum output tokens must be positive")
        endpoint = urlsplit(self.base_url)
        local_hosts = {"localhost", "127.0.0.1", "::1"}
        if not endpoint.hostname or (
            endpoint.scheme != "https"
            and not (endpoint.scheme == "http" and endpoint.hostname in local_hosts)
        ):
            raise ValueError("model base URL must use HTTPS or explicit localhost HTTP")


@dataclass(frozen=True, slots=True)
class ModelDescriptor:
    model_id: str
    display_name: str
    capabilities: ModelCapabilities
    runner_family: str


class ModelBinding(Protocol):
    @property
    def descriptor(self) -> ModelDescriptor: ...

    async def close(self) -> None: ...


class ModelAdapter(Protocol):
    @property
    def runner_family(self) -> str: ...

    async def open(
        self, configuration: ModelConfiguration, secret_resolver: SecretResolver
    ) -> ModelBinding: ...

    async def close(self) -> None: ...
