"""Static tool catalog and allow-list enforcing invoker."""

import asyncio
from collections.abc import Iterable

from agentle.foundation import AgentleError, ErrorCategory, ErrorInfo, error_info_from_exception

from .contracts import Tool, ToolCall, ToolDefinition, ToolInvocationContext, ToolResult


def _tool_error(code: str, message: str) -> AgentleError:
    return AgentleError(ErrorInfo(code=code, category=ErrorCategory.TOOL, message=message))


class ToolCatalog:
    def __init__(self, tools: Iterable[Tool]) -> None:
        self._tools: dict[str, Tool] = {}
        for tool in tools:
            name = tool.definition.name
            if name in self._tools:
                raise ValueError(f"duplicate tool name: {name}")
            self._tools[name] = tool

    def definitions_for(self, allowed_names: Iterable[str]) -> tuple[ToolDefinition, ...]:
        definitions: list[ToolDefinition] = []
        for name in allowed_names:
            tool = self._tools.get(name)
            if tool is None:
                raise _tool_error("tool.unknown", f"The configured tool '{name}' does not exist.")
            definitions.append(tool.definition)
        return tuple(definitions)

    def get(self, name: str) -> Tool | None:
        return self._tools.get(name)


class ToolInvoker:
    def __init__(self, catalog: ToolCatalog, allowed_names: Iterable[str]) -> None:
        self._catalog = catalog
        ordered_names = tuple(allowed_names)
        self._allowed_names = frozenset(ordered_names)
        self._definitions = catalog.definitions_for(ordered_names)

    @property
    def definitions(self) -> tuple[ToolDefinition, ...]:
        return self._definitions

    async def invoke(self, call: ToolCall, context: ToolInvocationContext) -> ToolResult:
        tool = self._catalog.get(call.name)
        if tool is None:
            raise _tool_error("tool.unknown", f"The requested tool '{call.name}' does not exist.")
        if call.name not in self._allowed_names:
            raise _tool_error(
                "tool.not_allowed", f"The requested tool '{call.name}' is not allowed."
            )
        try:
            return await tool.invoke(call, context)
        except (AgentleError, asyncio.CancelledError):
            raise
        except Exception as error:
            info = error_info_from_exception(error)
            raise AgentleError(
                ErrorInfo(
                    code="tool.failed",
                    category=ErrorCategory.TOOL,
                    message="The tool failed unexpectedly.",
                    cause_code=info.code,
                )
            ) from error
