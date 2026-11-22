"""What a conversation's page needs to list its tool calls: their inputs and API calls, long values cut short."""

import json
import logging
import re

__all__ = ["actions_json"]

logger = logging.getLogger(__name__)

# The length past which the page cuts a value in a pill and offers to show it whole (actions.js, MAX_INLINE).
SHOWN = 500
# What JavaScript's trim() removes: its white space and its line terminators.
JS_SPACE = "\t\n\v\f\r \u00a0\u1680\u2000\u2001\u2002\u2003\u2004\u2005\u2006\u2007\u2008\u2009\u200a\u2028\u2029\u202f\u205f\u3000\ufeff"


def refuse(constant: str):
    raise ValueError(f"{constant} is not JSON")


def stored(content: str):
    """A stored tool message as the page's JSON.parse reads it, which takes no NaN nor Infinity."""
    return json.loads(content, parse_constant=refuse)


def displayed(value) -> str:
    """A value as the page writes it in a pill: a string as it is, anything else as compact JSON."""
    return value if isinstance(value, str) else json.dumps(value, separators=(",", ":"), ensure_ascii=False)


def output_text(result: dict) -> str:
    """The text of a tool result without its API signal lines, as the page reads it (actions.js, toolOutputText)."""
    output = result.get("output", "")
    if isinstance(output, dict) and "output" in output:
        output = output["output"]
    if isinstance(output, list):
        texts = (block.get("text") if isinstance(block, dict) else None for block in output)
        output = "\n".join("" if text is None else displayed(text) for text in texts)
    elif not isinstance(output, str):
        output = json.dumps(output, indent=2, ensure_ascii=False)
    return re.sub(r"\[(?:AUTOMETA|MATOMETA):API:\{.*?\}\]\n?", "", output).strip(JS_SPACE)


def light_call(content: str) -> dict | str:
    """A tool call with each long input cut to what a pill shows, and the names of those cut."""
    call = stored(content)
    if not isinstance(call, dict):
        return content
    if not isinstance(call.get("input"), dict):
        return call
    texts = {name: displayed(value) for name, value in call["input"].items()}
    capped = [name for name, text in texts.items() if len(text) > SHOWN]
    light = {**call, "input": {**call["input"], **{name: texts[name][:SHOWN] for name in capped}}, "capped": capped}
    # Why: a pill reading a file is named after it; the name is at the end of a path, which the cut removes.
    if "file_path" in capped and isinstance(call["input"]["file_path"], str):
        light["file_name"] = call["input"]["file_path"].rsplit("/", 1)[-1][:SHOWN]
    return light


def light_result(content: str) -> dict:
    """Of a tool result, what a pill shows: its API calls and the start of its text; nothing when it made none."""
    result = stored(content) if content else {}
    if not isinstance(result, dict) or not result.get("api_calls"):
        return {}
    text = output_text(result)
    return {"api_calls": result["api_calls"], "output": text[:SHOWN], "output_capped": len(text) > SHOWN}


def light_message(message_id: int, kind: str, content: str) -> str:
    """A message as the page replays it for its pills, in JSON: id and type, content for a tool call or result."""
    light = {"id": message_id, "type": kind}
    if kind in ("tool_use", "tool_result"):
        try:
            light["content"] = light_call(content) if kind == "tool_use" else light_result(content)
            return json.dumps(light, ensure_ascii=False)
        except Exception:
            # Why: one message this cannot read or write must not take the pills of its whole conversation away;
            # the page then reads a call as it is stored, as it did, and a result as having no API call.
            logger.warning("Message %s could not be made light", message_id, exc_info=True)
            light["content"] = content if kind == "tool_use" else {}
    return json.dumps(light, ensure_ascii=False)


def actions_json(conv_id: str, messages: list[tuple[int, str, str]], queue: list, returned: list) -> str:
    """The body of the page's request for its pills: each message made light, what waits and what was handed back."""
    body = '{{"id": {}, "messages": [{}], "queue": {}, "returned": {}}}'.format(
        json.dumps(conv_id),
        ", ".join(light_message(*message) for message in messages),
        json.dumps(queue, ensure_ascii=False),
        json.dumps(returned, ensure_ascii=False),
    )
    # Why: a stored escape may name half of a character pair (text cut between the two); the page showed it as an
    # unknown character, and UTF-8 cannot carry it.
    return re.sub("[\ud800-\udfff]", "\ufffd", body)
