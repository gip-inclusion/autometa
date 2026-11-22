"""The tool calls of a conversation as the page lists them: a pill in the sidebar, a reference under an answer."""

import json
import logging
import re
from urllib.parse import quote

from lib.answer_html import safe_user_url

__all__ = ["pill", "value_text"]

logger = logging.getLogger(__name__)

# The length past which a pill cuts a value and offers to show it whole.
SHOWN = 500
# What JavaScript's trim() removes: its white space and its line terminators.
JS_SPACE = "\t\n\v\f\r                  　﻿"
ICONS = {
    "API:": "ri-cloud-line",
    "Read:": "ri-file-text-line",
    "Write:": "ri-file-add-line",
    "Edit:": "ri-edit-line",
    "Search:": "ri-search-line",
    "Execute:": "ri-play-line",
    "Query:": "ri-database-2-line",
    "Shell:": "ri-terminal-line",
    "Skill:": "ri-magic-line",
    "Thinking:": "ri-lightbulb-line",
    "System:": "ri-settings-3-line",
    "Web:": "ri-global-line",
    "Interaction:": "ri-question-line",
}
LABELS = {
    "API: Matomo": "API Matomo",
    "API: Metabase": "API Metabase",
    "API: Matomo + Metabase": "API Matomo + Metabase",
    "API: Matomo (curl)": "API Matomo (curl)",
    "API: GitHub": "API GitHub",
    "API: GitHub (clone)": "API GitHub (clone)",
    "API: curl": "API curl",
    "Read: knowledge": "Lecture de la base de connaissances",
    "Read: skill definition": "Lecture d'une définition de skill",
    "Read: skill code": "Lecture du code d'un skill",
    "Read: code": "Lecture du code",
    "Read: docs": "Lecture de la documentation",
    "Read: temp": "Lecture d'un fichier temporaire",
    "Read: other": "Lecture d'un fichier",
    "Write: temp": "Écriture d'un fichier temporaire",
    "Write: interactive": "Écriture d'une appli",
    "Write: script": "Rédaction d'un programme",
    "Write: knowledge": "Écriture dans la base de connaissances",
    "Write: other": "Écriture d'un fichier",
    "Edit: knowledge": "Modification de la base de connaissances",
    "Edit: skill": "Modification d'un skill",
    "Edit: code": "Modification du code",
    "Edit: other": "Modification d'un fichier",
    "Execute: script": "Exécution d'un programme",
    "Query: SQLite": "Requête SQLite",
    "Search: codebase": "Recherche dans le code",
    "Thinking: todo": "Réflexion",
    "System: task": "Liste de tâches",
    "Web: fetch": "Requête web",
    "Interaction: ask user": "Interaction",
}


def stored(content: str, fallback: dict) -> dict:
    """A stored tool message read as JSON; the fallback when it is not an object."""
    try:
        read = json.loads(content)
    except ValueError:
        return fallback
    # Why: a stored escape may name half of a character pair (text cut between the two), which UTF-8 cannot carry
    # to the page.
    if re.search(r"\\u[dD][89a-fA-F]", content):
        read = json.loads(re.sub("[\ud800-\udfff]", "\ufffd", json.dumps(read, ensure_ascii=False)))
    return read if isinstance(read, dict) else fallback


def displayed(value) -> str:
    """A value as a pill writes it: a string as it is, anything else as compact JSON."""
    return value if isinstance(value, str) else json.dumps(value, separators=(",", ":"), ensure_ascii=False)


def output_text(result: dict) -> str:
    """The text of a tool result, without its API signal lines."""
    output = result.get("output", "")
    if isinstance(output, dict) and "output" in output:
        output = output["output"]
    if isinstance(output, list):
        texts = (block.get("text") if isinstance(block, dict) else None for block in output)
        output = "\n".join("" if text is None else displayed(text) for text in texts)
    elif not isinstance(output, str):
        output = json.dumps(output, indent=2, ensure_ascii=False)
    return re.sub(r"\[(?:AUTOMETA|MATOMETA):API:\{.*?\}\]\n?", "", output).strip(JS_SPACE)


def clean_sql(sql: str) -> str:
    # Why: signals carry their SQL with literal "\n" at its head; the page has always dropped these along with spaces.
    return re.sub(r"^[\s\\n]+", "", sql)


def api_calls(result: dict) -> list[dict]:
    calls = result.get("api_calls")
    return [call for call in calls if isinstance(call, dict)] if isinstance(calls, list) else []


def labels(category: str, use: dict, calls: list[dict]) -> tuple[str, str | None]:
    """A pill's name, and the count of API calls made by a tool that is not one itself."""
    label = LABELS.get(category, category) or "Action"
    path = use["input"].get("file_path") if isinstance(use.get("input"), dict) else None
    if category.startswith("Read:") and isinstance(path, str) and path:
        label = path.rsplit("/", 1)[-1]
    if not calls:
        return label, None
    if category.startswith("API:"):
        return calls[0].get("method") or ("Requête SQL" if calls[0].get("sql") else label), None
    counts = {}
    for call in calls:
        source = str(call.get("source") or "API")
        counts[source] = counts.get(source, 0) + 1
    summary = ", ".join(
        f"{count} requête{'s' if count > 1 else ''} {source[:1].upper()}{source[1:]}"
        for source, count in counts.items()
    )
    return label, summary


def values(use: dict, result: dict, calls: list[dict], linked: bool, address: str) -> list[dict]:
    """What a pill shows of a call once opened: each input, then its result's text when it called an API."""
    if not isinstance(use.get("input"), dict):
        return [{"key": "INPUT", "text": str(use["input"])}] if use.get("input") else []
    entries = sorted(use["input"].items(), key=lambda entry: entry[0] != "description")
    shown = [
        {"key": key, "text": displayed(value), "whole": f"{address}/{use['id']}/value?input={quote(key, safe='')}"}
        for key, value in entries
        # Why: a knowledge file is linked above; its path would say it twice.
        if not (key == "file_path" and linked)
    ]
    if calls:
        shown.append({"key": "résultat", "text": output_text(result), "whole": f"{address}/{result['id']}/value"})
    return [
        {
            **entry,
            "key": entry["key"].upper(),
            "description": entry["key"] == "description",
            "code": entry["key"] in ("command", "query", "content", "résultat"),
            "cut": len(entry["text"]) > SHOWN,
            "text": entry["text"][:SHOWN] + "..." * (len(entry["text"]) > SHOWN),
        }
        for entry in shown
    ]


def pill(conv_id: str, index: int, use: tuple[int, str], result: tuple[int, str]) -> dict:
    """What the page shows of a tool call and its result; a bare pill when the call cannot be read."""
    try:
        return described(conv_id, index, use, result)
    except Exception:
        # Why: one call this cannot read must not take away its conversation's page, nor the other pills.
        logger.warning("Tool call %s could not be described", use[0], exc_info=True)
        return {"index": index, "message": result[0], "icon": "ri-tools-line", "label": "Action", "data": False}


def described(conv_id: str, index: int, use: tuple[int, str], result: tuple[int, str]) -> dict:
    """Of a tool call and its result: icon and names, links, values cut to what a pill holds."""
    read = {**stored(use[1], {"tool": "unknown", "input": use[1]}), "id": use[0]}
    answer = {**stored(result[1], {}), "id": result[0]}
    category = str(read.get("category") or f"Other: {read.get('tool')}")
    calls = api_calls(answer)
    label, summary = labels(str(read.get("category") or ""), read, calls)
    path = read["input"].get("file_path") if isinstance(read.get("input"), dict) else None
    knowledge = category == "Read: knowledge" and isinstance(path, str) and re.search(r"/knowledge/(.+)$", path)
    address = f"/api/conversations/{conv_id}/messages"
    return {
        "index": index,
        "message": result[0],
        "icon": next((icon for prefix, icon in ICONS.items() if category.startswith(prefix)), "ri-tools-line"),
        "label": label,
        "summary": summary,
        "data": category == "Read: knowledge" or bool(calls),
        "knowledge": knowledge and {"path": knowledge[1], "name": knowledge[1].rsplit("/", 1)[-1]},
        "calls": [
            {
                "text": call.get("method") or (f"{clean_sql(str(call['sql']))[:50]}..." if call.get("sql") else "View"),
                "icon": "ri-bar-chart-line" if call.get("source") == "matomo" else "ri-database-2-line",
                # Why: the signal is read from the tool's output, which the agent or a page it fetched can forge.
                "href": call["url"] if isinstance(call.get("url"), str) and safe_user_url(call["url"]) else None,
                "sql": clean_sql(str(call["sql"]))[:200] + "..." * (len(clean_sql(str(call["sql"]))) > 200)
                if call.get("sql")
                else None,
                "whole": f"{address}/{result[0]}/value?sql={n}"
                if call.get("sql") and len(clean_sql(str(call["sql"]))) > 200
                else None,
            }
            for n, call in enumerate(calls)
        ],
        "values": values(read, answer, calls, bool(knowledge), address),
    }


def value_text(content: str, input_key: str | None, sql: int | None) -> str | None:
    """A value of a stored tool message whole: one input of a call, the SQL of an API call, else the result's text."""
    read = stored(content, {})
    if input_key is not None:
        held = read.get("input") if isinstance(read.get("input"), dict) else {}
        return displayed(held[input_key]) if input_key in held else None
    if sql is not None:
        calls = api_calls(read)
        return clean_sql(str(calls[sql]["sql"])) if 0 <= sql < len(calls) and calls[sql].get("sql") else None
    return output_text(read or {"output": content})
