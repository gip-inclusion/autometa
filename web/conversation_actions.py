"""What a conversation's page needs to list its tool calls: their inputs and API calls, long values cut short."""

import json
import re

__all__ = ["light_messages"]

# The length past which the page cuts a value in a pill and offers to show it whole (actions.js, MAX_INLINE).
SHOWN = 500


def displayed(value) -> str:
    """A value as the page writes it in a pill: a string as it is, anything else as compact JSON."""
    return value if isinstance(value, str) else json.dumps(value, separators=(",", ":"), ensure_ascii=False)


def output_text(result: dict) -> str:
    """The text of a tool result without its API signal lines, as the page reads it (actions.js, toolOutputText)."""
    output = result.get("output")
    if isinstance(output, dict) and "output" in output:
        output = output["output"]
    if isinstance(output, list):
        output = "\n".join((block.get("text") or "") if isinstance(block, dict) else "" for block in output)
    elif not isinstance(output, str):
        output = json.dumps(output, indent=2, ensure_ascii=False)
    return re.sub(r"\[(?:AUTOMETA|MATOMETA):API:\{.*?\}\]\n?", "", output).strip()


def light_call(content: str) -> dict | str:
    """A tool call with each long input cut to what a pill shows, and the names of those cut."""
    try:
        call = json.loads(content)
    except ValueError:
        return content
    if not isinstance(call, dict):
        return content
    if not isinstance(call.get("input"), dict):
        return call
    texts = {name: displayed(value) for name, value in call["input"].items()}
    capped = [name for name, text in texts.items() if len(text) > SHOWN]
    return {**call, "input": {**call["input"], **{name: texts[name][:SHOWN] for name in capped}}, "capped": capped}


def light_result(content: str) -> dict:
    """Of a tool result, what a pill shows: its API calls and the start of its text; nothing when it made none."""
    try:
        result = json.loads(content)
    except ValueError:
        return {}
    if not isinstance(result, dict) or not result.get("api_calls"):
        return {}
    text = output_text(result)
    return {"api_calls": result["api_calls"], "output": text[:SHOWN], "output_capped": len(text) > SHOWN}


def light_messages(messages: list[tuple[int, str, str]]) -> list[dict]:
    """Each message of a conversation as the page replays it for its pills: id and type, content for tool calls."""
    light = {"tool_use": light_call, "tool_result": light_result}
    return [
        {"id": message_id, "type": kind, **({"content": light[kind](content)} if kind in light else {})}
        for message_id, kind, content in messages
    ]
