from uuid import UUID

from agentle.foundation import (
    new_command_id,
    new_event_id,
    new_execution_id,
    new_run_id,
    new_session_id,
    new_tool_call_id,
)


def test_id_factories_return_distinct_uuid_strings() -> None:
    values = {
        new_session_id(),
        new_run_id(),
        new_command_id(),
        new_event_id(),
        new_tool_call_id(),
        new_execution_id(),
    }

    assert len(values) == 6
    assert all(str(UUID(value)) == value for value in values)
