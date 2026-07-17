"""Pydantic AI single-agent runner and native-tool bridge."""

import asyncio
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Any, cast

import openai
from pydantic_ai import (
    Agent,
    AgentRunResultEvent,
    FunctionToolCallEvent,
    FunctionToolResultEvent,
    ModelRequest,
    ModelResponse,
    PartDeltaEvent,
    PartStartEvent,
    RunContext,
    TextPart,
    TextPartDelta,
    Tool,
    ToolCallPart,
    UserPromptPart,
)
from pydantic_ai.exceptions import (
    ModelAPIError,
    ModelHTTPError,
    UnexpectedModelBehavior,
    UserError,
)
from pydantic_ai.messages import ModelMessage

from agentle.agents.contracts import (
    AgentRunEvent,
    AgentRunInput,
    FinalOutput,
    TextDelta,
    ToolCompleted,
    ToolFailed,
    ToolRequested,
    ToolStarted,
    UsageUpdated,
)
from agentle.context import MessageRole
from agentle.foundation import (
    AgentleError,
    ErrorCategory,
    ErrorInfo,
    ToolCallId,
    error_info_from_exception,
)
from agentle.models import PYDANTIC_AI_RUNNER_FAMILY
from agentle.models.adapters.pydantic_ai_openai import _PydanticAIModelBinding
from agentle.tools import ToolCall, ToolInvocationContext, ToolJson, ToolResult

type _ToolOutcome = ToolResult | ErrorInfo


@dataclass(slots=True)
class _RunDependencies:
    run_input: AgentRunInput
    outcomes: dict[str, _ToolOutcome] = field(default_factory=dict)


def _framework_error(error: Exception) -> AgentleError:
    code = "agent.framework_failure"
    category = ErrorCategory.PROVIDER
    retryable = False
    if isinstance(error, ModelHTTPError):
        if error.status_code in {401, 403}:
            code = "model.authentication"
        elif error.status_code == 429:
            code, retryable = "model.rate_limited", True
        elif error.status_code >= 500:
            code, retryable = "model.unavailable", True
        else:
            code = "model.protocol"
    elif isinstance(error, ModelAPIError):
        cause: BaseException | None = error.__cause__
        while cause is not None and not isinstance(cause, openai.APIConnectionError):
            cause = cause.__cause__
        if isinstance(cause, openai.APITimeoutError):
            return AgentleError(
                ErrorInfo(
                    code="model.timeout",
                    category=ErrorCategory.TIMEOUT,
                    message="The model request timed out.",
                    retryable=True,
                )
            )
        code, retryable = "model.unavailable", True
    elif isinstance(error, openai.AuthenticationError):
        code = "model.authentication"
    elif isinstance(error, openai.RateLimitError):
        code, retryable = "model.rate_limited", True
    elif isinstance(error, openai.APITimeoutError):
        return AgentleError(
            ErrorInfo(
                code="model.timeout",
                category=ErrorCategory.TIMEOUT,
                message="The model request timed out.",
                retryable=True,
            )
        )
    elif isinstance(error, openai.APIConnectionError):
        code, retryable = "model.unavailable", True
    elif isinstance(error, openai.APIStatusError):
        code = "model.protocol"
    elif isinstance(error, (UnexpectedModelBehavior, UserError)):
        category = ErrorCategory.INTERNAL
    return AgentleError(
        ErrorInfo(
            code=code,
            category=category,
            message="The agent framework or model provider failed.",
            retryable=retryable,
        )
    )


def _as_tool_json(value: object) -> ToolJson:
    if value is None or isinstance(value, (str, bool, int, float)):
        return value
    if isinstance(value, list):
        return [_as_tool_json(item) for item in value]
    if isinstance(value, dict) and all(isinstance(key, str) for key in value):
        return {str(key): _as_tool_json(item) for key, item in value.items()}
    raise AgentleError(
        ErrorInfo(
            code="agent.framework_failure",
            category=ErrorCategory.INTERNAL,
            message="The framework produced non-JSON tool arguments.",
        )
    )


def _tool_arguments(part: ToolCallPart) -> dict[str, ToolJson]:
    value = _as_tool_json(part.args_as_dict(raise_if_invalid=True))
    if not isinstance(value, dict):
        raise AssertionError("tool arguments must be an object")
    return value


def _message_history(run_input: AgentRunInput) -> list[ModelMessage]:
    history: list[ModelMessage] = []
    for message in run_input.context.messages:
        if message.role is MessageRole.USER:
            history.append(ModelRequest(parts=[UserPromptPart(message.content)]))
        else:
            history.append(ModelResponse(parts=[TextPart(message.content)]))
    return history


def _make_tool(
    definition_name: str,
    description: str,
    input_schema: dict[str, ToolJson],
) -> Tool[_RunDependencies]:
    async def invoke(ctx: RunContext[_RunDependencies], **arguments: Any) -> object:
        call_id = ctx.tool_call_id
        if call_id is None:
            raise AgentleError(
                ErrorInfo(
                    code="agent.framework_failure",
                    category=ErrorCategory.INTERNAL,
                    message="The framework omitted a tool call identifier.",
                )
            )
        run_input = ctx.deps.run_input
        try:
            result = await run_input.tool_invoker.invoke(
                ToolCall(
                    call_id=ToolCallId(call_id),
                    name=definition_name,
                    arguments={key: _as_tool_json(value) for key, value in arguments.items()},
                ),
                ToolInvocationContext(
                    session_id=run_input.session_id,
                    run_id=run_input.run_id,
                    workspace=run_input.workspace,
                    deadline=run_input.deadline,
                    cancellation=run_input.cancellation,
                ),
            )
        except asyncio.CancelledError:
            raise
        except Exception as error:
            info = error_info_from_exception(error)
            ctx.deps.outcomes[call_id] = info
            return {"error": info.to_dict()}
        ctx.deps.outcomes[call_id] = result
        return {
            "content": result.content,
            "media_type": result.media_type,
            "truncated": result.truncated,
            "metadata": result.metadata,
        }

    return Tool.from_schema(
        invoke,
        name=definition_name,
        description=description,
        json_schema=cast(dict[str, Any], input_schema),
        takes_ctx=True,
        sequential=True,
    )


class PydanticAISingleAgentRunner:
    runner_family = PYDANTIC_AI_RUNNER_FAMILY

    def __init__(self) -> None:
        self._closed = False

    async def _run(self, run_input: AgentRunInput) -> AsyncIterator[AgentRunEvent]:
        if self._closed:
            raise AgentleError(
                ErrorInfo(
                    code="agent.runner_closed",
                    category=ErrorCategory.INTERNAL,
                    message="The agent runner is closed.",
                )
            )
        if not isinstance(run_input.model, _PydanticAIModelBinding):
            raise AgentleError(
                ErrorInfo(
                    code="agent.model_incompatible",
                    category=ErrorCategory.CONFIGURATION,
                    message="The model binding is incompatible with this runner.",
                )
            )
        tools = [
            _make_tool(definition.name, definition.description, definition.input_schema)
            for definition in run_input.tool_invoker.definitions
        ]
        dependencies = _RunDependencies(run_input)
        agent = Agent[_RunDependencies, str](
            run_input.model.native_model,
            output_type=str,
            instructions=run_input.context.instructions,
            deps_type=_RunDependencies,
            tools=tools,
            model_settings=run_input.model.model_settings,
            retries=0,
        )
        try:
            async with agent.run_stream_events(
                run_input.context.current_request,
                message_history=_message_history(run_input),
                deps=dependencies,
            ) as events:
                async for event in events:
                    run_input.cancellation.raise_if_cancelled()
                    if isinstance(event, PartStartEvent) and isinstance(event.part, TextPart):
                        if event.part.content:
                            yield TextDelta(event.part.content)
                    elif isinstance(event, PartDeltaEvent) and isinstance(
                        event.delta, TextPartDelta
                    ):
                        if event.delta.content_delta:
                            yield TextDelta(event.delta.content_delta)
                    elif isinstance(event, FunctionToolCallEvent):
                        part = event.part
                        requested_call_id = ToolCallId(part.tool_call_id)
                        yield ToolRequested(
                            requested_call_id, part.tool_name, _tool_arguments(part)
                        )
                        yield ToolStarted(requested_call_id, part.tool_name)
                    elif isinstance(event, FunctionToolResultEvent):
                        call_id = event.tool_call_id
                        outcome = dependencies.outcomes.pop(call_id, None)
                        name = event.part.tool_name
                        if name is None:
                            raise AgentleError(
                                ErrorInfo(
                                    code="agent.framework_failure",
                                    category=ErrorCategory.INTERNAL,
                                    message="The framework omitted the tool result name.",
                                )
                            )
                        if isinstance(outcome, ToolResult):
                            yield ToolCompleted(ToolCallId(call_id), name, outcome.truncated)
                        elif isinstance(outcome, ErrorInfo):
                            yield ToolFailed(ToolCallId(call_id), name, outcome)
                        else:
                            raise AgentleError(
                                ErrorInfo(
                                    code="agent.framework_failure",
                                    category=ErrorCategory.INTERNAL,
                                    message="The framework returned an unknown tool outcome.",
                                )
                            )
                    elif isinstance(event, AgentRunResultEvent):
                        usage = event.result.usage
                        yield UsageUpdated(usage.input_tokens, usage.output_tokens)
                        if not isinstance(event.result.output, str):
                            raise AgentleError(
                                ErrorInfo(
                                    code="agent.invalid_output",
                                    category=ErrorCategory.INTERNAL,
                                    message="The agent returned a non-text output.",
                                )
                            )
                        yield FinalOutput(event.result.output)
        except (AgentleError, asyncio.CancelledError):
            raise
        except Exception as error:
            raise _framework_error(error) from error

    def run(self, run_input: AgentRunInput) -> AsyncIterator[AgentRunEvent]:
        return self._run(run_input)

    async def close(self) -> None:
        self._closed = True
