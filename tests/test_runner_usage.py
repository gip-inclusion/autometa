"""L'usage est attribué au moteur qui a réellement joué le tour."""

import pytest

from web import runner


@pytest.mark.parametrize(
    "record",
    [
        lambda backend: runner._record_usage(
            "c1",
            {"message": {"id": "m1", "model": "glm-5.2", "usage": {"output_tokens": 12}}},
            runner.RunUsage(),
            backend,
        ),
        lambda backend: runner._record_thinking_tail(
            "c1",
            {"output_tokens": 1717},
            runner.RunUsage(output_total=141, last_model="glm-5.2"),
            backend,
        ),
    ],
    ids=["record_usage", "record_thinking_tail"],
)
def test_usage_is_attributed_to_the_running_backend(mocker, record):
    mocker.patch.object(runner.config, "AGENT_BACKEND", "cli")
    insert = mocker.patch.object(runner.store, "insert_usage_event")

    record("cli-ollama")

    assert insert.call_args.kwargs["backend"] == "cli-ollama"
