"""Secret references and explicit resolution adapters."""

import os
import re
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Protocol

from .errors import AgentleError, ErrorCategory, ErrorInfo

_ENV_NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


@dataclass(frozen=True, slots=True)
class SecretRef:
    scheme: str
    name: str

    @classmethod
    def parse(cls, value: str) -> "SecretRef":
        scheme, separator, name = value.partition(":")
        if separator != ":" or not scheme or not name:
            raise ValueError("secret reference must use the form '<scheme>:<name>'")
        if scheme != "env":
            raise ValueError(f"unsupported secret reference scheme: {scheme}")
        if not _ENV_NAME.fullmatch(name):
            raise ValueError("environment secret name is invalid")
        return cls(scheme=scheme, name=name)

    def __str__(self) -> str:
        return f"{self.scheme}:{self.name}"


class SecretResolver(Protocol):
    def resolve(self, reference: SecretRef) -> str: ...


class EnvironmentSecretResolver:
    """Resolve ``env:`` references from an injected or process environment."""

    def __init__(self, environment: Mapping[str, str] | None = None) -> None:
        self._environment = os.environ if environment is None else environment

    def resolve(self, reference: SecretRef) -> str:
        if reference.scheme != "env":
            raise AgentleError(
                ErrorInfo(
                    code="configuration.secret_scheme",
                    category=ErrorCategory.CONFIGURATION,
                    message="The secret reference scheme is not supported.",
                )
            )
        value = self._environment.get(reference.name)
        if value is None:
            raise AgentleError(
                ErrorInfo(
                    code="configuration.secret_missing",
                    category=ErrorCategory.CONFIGURATION,
                    message=f"Required secret reference '{reference}' is not configured.",
                    details={"reference": str(reference)},
                )
            )
        return value
