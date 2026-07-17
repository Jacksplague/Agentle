import pytest

from agentle.agents import AgentDefinition


def test_agent_definition_preserves_ordered_tool_allow_list() -> None:
    definition = AgentDefinition(
        agent_id="default",
        display_name="Default",
        instructions="Be helpful.",
        model_id="default",
        allowed_tools=("read_text",),
    )

    assert definition.allowed_tools == ("read_text",)


def test_agent_definition_rejects_duplicate_tools() -> None:
    with pytest.raises(ValueError, match="duplicates"):
        AgentDefinition(
            agent_id="default",
            display_name="Default",
            instructions="Be helpful.",
            model_id="default",
            allowed_tools=("read_text", "read_text"),
        )
