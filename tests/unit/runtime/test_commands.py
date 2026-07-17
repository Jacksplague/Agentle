import pytest

from agentle.foundation import AgentleError, RunId, SessionId
from agentle.runtime import CancelRun, CreateSession, Shutdown, SubmitPrompt


def test_commands_receive_distinct_ids() -> None:
    commands = [
        CreateSession(title="Test"),
        SubmitPrompt(
            session_id=SessionId("session"),
            text="hello",
            agent_id="default",
            timeout_seconds=30,
        ),
        CancelRun(run_id=RunId("run")),
        Shutdown(grace_seconds=2),
    ]

    assert len({command.command_id for command in commands}) == len(commands)


@pytest.mark.parametrize(
    "factory,code",
    [
        (
            lambda: SubmitPrompt(
                session_id=SessionId("session"),
                text="  ",
                agent_id="default",
                timeout_seconds=30,
            ),
            "runtime.empty_prompt",
        ),
        (
            lambda: SubmitPrompt(
                session_id=SessionId("session"),
                text="hello",
                agent_id="default",
                timeout_seconds=0,
            ),
            "runtime.invalid_timeout",
        ),
        (lambda: Shutdown(grace_seconds=-1), "runtime.invalid_shutdown_grace"),
    ],
)
def test_invalid_commands_raise_structured_errors(factory: object, code: str) -> None:
    with pytest.raises(AgentleError) as caught:
        assert callable(factory)
        factory()

    assert caught.value.info.code == code
