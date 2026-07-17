"""Read-only native text tool backed by Execution."""

from agentle.execution import ExecutionBackend, ExecutionControl, FileReadRequest
from agentle.foundation import AgentleError, ErrorCategory, ErrorInfo

from .contracts import (
    SideEffect,
    ToolCall,
    ToolDefinition,
    ToolInvocationContext,
    ToolJson,
    ToolResult,
)


def _invalid_arguments(message: str) -> AgentleError:
    return AgentleError(
        ErrorInfo(code="tool.invalid_arguments", category=ErrorCategory.TOOL, message=message)
    )


class ReadTextTool:
    def __init__(
        self,
        backend: ExecutionBackend,
        *,
        default_max_lines: int = 200,
        maximum_lines: int = 500,
        maximum_bytes: int = 65_536,
    ) -> None:
        if not 1 <= default_max_lines <= maximum_lines:
            raise ValueError("default line limit must fit within the maximum")
        if maximum_bytes < 1:
            raise ValueError("maximum byte count must be positive")
        self._backend = backend
        self._default_max_lines = default_max_lines
        self._maximum_lines = maximum_lines
        self._maximum_bytes = maximum_bytes
        self._definition = ToolDefinition(
            name="read_text",
            description="Read a bounded range of UTF-8 text from the active workspace.",
            input_schema={
                "type": "object",
                "additionalProperties": False,
                "required": ["path"],
                "properties": {
                    "path": {"type": "string"},
                    "start_line": {"type": "integer", "minimum": 1},
                    "max_lines": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": maximum_lines,
                    },
                },
            },
            side_effect=SideEffect.READ_ONLY,
        )

    @property
    def definition(self) -> ToolDefinition:
        return self._definition

    async def invoke(self, call: ToolCall, context: ToolInvocationContext) -> ToolResult:
        if call.name != self.definition.name:
            raise _invalid_arguments("The tool call name does not match the implementation.")
        path = self._string_argument(call.arguments, "path", required=True)
        start_line = self._integer_argument(call.arguments, "start_line", default=1)
        max_lines = self._integer_argument(
            call.arguments, "max_lines", default=self._default_max_lines
        )
        unexpected = set(call.arguments) - {"path", "start_line", "max_lines"}
        if unexpected:
            raise _invalid_arguments("The tool call contains unsupported arguments.")
        if start_line < 1 or not 1 <= max_lines <= self._maximum_lines:
            raise _invalid_arguments("The requested line range is outside the allowed bounds.")
        result = await self._backend.read_text(
            FileReadRequest(
                path=path,
                start_line=start_line,
                max_lines=max_lines,
                max_bytes=self._maximum_bytes,
            ),
            ExecutionControl(
                deadline=context.deadline,
                cancellation=context.cancellation,
            ),
        )
        return ToolResult(
            content=result.text,
            media_type=self.definition.output_media_type,
            truncated=result.truncated,
            metadata={"lines": result.lines},
        )

    @staticmethod
    def _string_argument(
        arguments: dict[str, ToolJson], name: str, *, required: bool
    ) -> str:
        value = arguments.get(name)
        if value is None and not required:
            return ""
        if not isinstance(value, str) or not value:
            raise _invalid_arguments(f"Argument '{name}' must be a non-empty string.")
        return value

    @staticmethod
    def _integer_argument(arguments: dict[str, ToolJson], name: str, *, default: int) -> int:
        value = arguments.get(name, default)
        if not isinstance(value, int) or isinstance(value, bool):
            raise _invalid_arguments(f"Argument '{name}' must be an integer.")
        return value
