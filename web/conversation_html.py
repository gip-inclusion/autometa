"""A conversation as the HTML of its page: questions, answers, report cards, limit notices, action pills; on open and as a turn runs."""

import json
import logging
import re
from dataclasses import replace
from decimal import ROUND_HALF_UP, Decimal

from markupsafe import Markup, escape

from lib import permalinks
from lib.answer_html import Link, render_answer, render_user
from web import conversation_actions
from web.database import store

logger = logging.getLogger(__name__)

# What follows the name of an attached file in a question: its properties, then its text when it is short.
FILE_PROPERTIES = re.compile(r"\]\n(?:- [^\n]+\n)+(?:```[\s\S]*?```\n?)?")


def file_blocks(content: str) -> list[tuple[int, int, str]]:
    """Where web/uploads.py described an attached file in a question: (start, end, file name), in order."""
    found, start, bracket = [], content.find("[Uploaded file: "), -1
    while start != -1:
        name = start + len("[Uploaded file: ")
        # Why: the bracket that closes a name is looked for once, however many openings come before it.
        if bracket < name:
            bracket = content.find("]", name)
            if bracket == -1:
                break
        properties = FILE_PROPERTIES.match(content, bracket) if bracket > name else None
        if properties:
            found.append((start, properties.end(), content[name:bracket]))
        start = content.find("[Uploaded file: ", properties.end() if properties else name)
    return found


def file_size(size: int) -> str:
    """A size as the composer writes it: one decimal, a half rounded up."""
    if size < 1024:
        return f"{size} o"
    unit, name = (1024, "Ko") if size < 1024**2 else (1024**2, "Mo")
    return f"{Decimal(size / unit).quantize(Decimal('0.1'), ROUND_HALF_UP)} {name}"


def file_icon(mime: str) -> str:
    if mime.startswith("image/"):
        return "ri-image-line"
    if mime.startswith("text/") or "json" in mime or "xml" in mime:
        return "ri-file-text-line"
    if "pdf" in mime:
        return "ri-file-pdf-line"
    if any(word in mime for word in ("spreadsheet", "excel", "csv")):
        return "ri-file-excel-line"
    return "ri-file-word-line" if "word" in mime or "document" in mime else "ri-file-line"


def file_pill(name: str, block: str) -> Markup:
    size = re.search(r"- Size: ([0-9,]+) bytes", block)
    mime = (re.search(r"- Type: ([^\n]+)", block) or ["", ""])[1]
    shown = size and Markup(' <span class="file-context-size">({})</span>').format(
        file_size(int(size[1].replace(",", "")))
    )
    return Markup('<span class="file-context-pill" title="{}"><i class="{}"></i> {}{}</span>').format(
        mime, file_icon(mime), name, shown or ""
    )


def user_html(content: str) -> Markup:
    """A question: its attached files as pills, then its text."""
    blocks, text, at = file_blocks(content), [], 0
    for start, end, _ in blocks:
        text.append(content[at:start])
        at = end
    text = "".join([*text, content[at:]])
    if blocks:
        text = re.sub(r"^\s*---\n", "", text).strip()
    # Why: past the length the queue accepts for waiting messages, a question is shown as typed, without Markdown;
    # reading it would hold the server's only worker for seconds.
    if len(text) > 20_000:
        rendered = escape(text).replace("\n", Markup("<br>"))
    else:
        rendered = Markup(render_user(text))
    shown = Markup('<div class="user-text">{}</div>').format(rendered) if text or not blocks else ""
    if not blocks:
        return shown
    pills = [file_pill(name, content[start:end]) for start, end, name in blocks]
    return Markup('<div class="file-context-pills">{}</div>{}').format(Markup().join(pills), shown)


def permalink_button(url: str, label: str) -> Markup:
    return Markup(
        '<button type="button" class="permalink-btn" data-url="{0}" title="Copier le lien vers {1}" '
        'aria-label="Copier le lien vers {1}"><i class="ri-link" aria-hidden="true"></i></button>'
    ).format(url, label)


def answer_anchors(parts: list[tuple[int, str]]) -> list[tuple[int, int, permalinks.Anchor]]:
    """Each section, table and chart of an answer: its message, that message's first line once joined, its anchor."""
    found, line, glued = [], 0, False
    for message_id, content in parts:
        content = content.replace("\r\n", "\n")
        # Why: a lone carriage return is a line break for the renderer and not for the slicer; lines would not agree.
        if "\r" in content:
            return []
        # Why: joined to a message that does not end its last line, a first line starts no element.
        found += [(message_id, line, a) for a in permalinks.anchors(content) if a.start or not glued]
        line += content.count("\n")
        if content:
            glued = not content.endswith("\n")
    return found


def element_links(conv_id: str, parts: list[tuple[int, str]], skipped: int, alone: bool) -> tuple[Link, ...]:
    """The link of each section, table and chart of an answer, at its line in the text once its messages are joined."""
    links = []
    labels = {"section": "cette section", "table": "ce tableau", "chart": "ce graphique"}
    for message_id, first, anchor in answer_anchors(parts):
        line = first - skipped
        url = f"/c/{conv_id}/{message_id}/{anchor.kind}-{anchor.rank}-{anchor.digest}"
        attributes = Markup(
            'data-anchor="{}-{}-{}" data-anchor-kind="{}" data-anchor-title="{}" data-anchor-level="{}" '
            'data-anchor-url="{}"'
        ).format(message_id, anchor.kind, anchor.rank, anchor.kind, anchor.title, anchor.level, url)
        links.append(
            Link(
                anchor.kind,
                line + anchor.start,
                line + anchor.end,
                anchor.level,
                attributes,
                permalink_button(url, labels[anchor.kind]),
            )
        )
    return tuple(whole_turn_unlinked(links, parts, skipped, alone))


def whole_turn_unlinked(links: list[Link], parts: list[tuple[int, str]], skipped: int, alone: bool) -> list[Link]:
    """The links, without the button of a section that is all its turn says: the answer's own link names the same."""
    sections = [link for link in links if link.kind == "section"]
    lines = "".join(content for _, content in parts).replace("\r\n", "\n").split("\n")[skipped:]
    first = next((n for n, line in enumerate(lines) if line.strip()), None)
    # Why: a section runs through the answers after its own; where the turn says more than this answer, the answer's
    # link names less than the section, which then keeps its own.
    if not alone or not sections or sections[0].start != first:
        return links
    if any(s.level <= sections[0].level for s in sections[1:]):
        return links
    return [replace(link, button=Markup("")) if link is sections[0] else link for link in links]


def report_file(text: str) -> str | None:
    """The first report file name in a text: YYYY-MM-, then letters, digits, hyphens or underscores, then .md."""
    # Why: read word by word; tried from each of its dates, a long word that ends in no .md would be read as many times.
    for word in re.finditer(r"[A-Za-z0-9_-]+", text):
        if text.startswith(".md", word.end()) and (name := re.search(r"[0-9]{4}-[0-9]{2}-[A-Za-z0-9_-]", word[0])):
            return f"{word[0][name.start() :]}.md"
    return None


def report_header(text: str, front_matter: str) -> Markup:
    """The header of an answer that opens with front matter: its category, date, site and the report file it names."""
    fields = {}
    for line in front_matter.split("\n"):
        name, _, rest = line.partition(":")
        # Why: as the page's JavaScript reads a field — an ASCII name, then spaces, then what is left of the line
        # after its last line terminator; read by hand, since a regex tries each run of spaces again and again.
        value = rest[max(rest.rfind(end) for end in "\r\u2028\u2029") + 1 :]
        blank = rest[: len(rest) - len(value)]
        if re.fullmatch(r"[A-Za-z0-9_][A-Za-z0-9_\s]*", name) and value and (not blank or blank.isspace()):
            fields[name.strip()] = value.strip()
    header = Markup('<div class="report-title"><i class="ri-file-text-line"></i> {}</div>').format(
        fields.get("query category") or "Rapport"
    )
    for name, icon in (("date", "ri-calendar-line"), ("website", "ri-global-line")):
        if fields.get(name):
            header += Markup('<div class="report-meta"><i class="{}"></i> {}</div>').format(icon, fields[name])
    if filename := report_file(text):
        header += Markup(
            '<a href="/api/reports/{}" target="_blank" class="report-link">'
            '<i class="ri-external-link-line"></i> Voir le rapport complet</a>'
        ).format(filename)
    return Markup('<div class="report-header">{}</div>').format(header)


def answer_block(conv_id: str, parts: list[tuple[int, str]], partial: bool, alone: bool) -> dict:
    """An answer: consecutive agent messages read as one text. One still being written has no link yet."""
    text = "".join(content for _, content in parts)
    front_matter = re.match(r"---\n(.*?)\n---\n", text, re.S)
    start = front_matter.end() if front_matter else 0
    links = () if partial else element_links(conv_id, parts, text[:start].count("\n"), alone)
    body = Markup(render_answer(text[start:], links))
    if front_matter:
        body = report_header(text, front_matter[1]) + Markup('<div class="report-body">{}</div>').format(body)
    link = "" if partial else permalink_button(f"/c/{conv_id}/{parts[0][0]}", "cette réponse")
    return {"report": bool(front_matter), "html": link + body}


def report_card(content: str) -> Markup:
    """The card of a saved report, from the JSON the agent's tool left."""
    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        data = None
    data = data if isinstance(data, dict) else {}
    ids = (i for i in (data.get("report_id"), data.get("id")) if isinstance(i, int | float) and not isinstance(i, bool))
    return Markup(
        '<div class="report-card-inline"><a href="/rapports/{}" class="report-card-link">'
        '<i class="ri-file-text-line"></i><span class="report-card-title">{}</span>'
        '<i class="ri-arrow-right-s-line"></i></a></div>'
    ).format(next(ids, 0), data.get("title") or "Rapport")


def block(conv_id: str, kind: str, parts: list[tuple[int, str]], partial: bool, alone: bool) -> dict:
    """A block's HTML, and whether it is a report; its text alone when the renderer cannot read it."""
    try:
        if kind == "assistant":
            return answer_block(conv_id, parts, partial, alone)
        content = parts[0][1]
        if kind == "user":
            return {"html": user_html(content)}
        if kind == "report":
            return {"html": report_card(content)}
        return {"html": Markup('<i class="ri-time-line" aria-hidden="true"></i><div>{}</div>').format(content)}
    except Exception:
        # Why: a message the renderer cannot read must not make its whole conversation impossible to open.
        # Why: the conversation's id comes from the address asked for, which a log must not repeat as it is; the
        # message's, read from the database, names the conversation as well.
        logger.exception("Block %s could not be rendered", parts[0][0])
        return {"html": Markup("<pre>{}</pre>").format("".join(content for _, content in parts))}


def reference(action: dict) -> Markup:
    return Markup('<span class="action-footnote" data-action-index="{}" title="{}"><i class="{}"></i></span>').format(
        action["index"], action["label"], action["icon"]
    )


def grouping(messages: list[tuple[int, str, str]]) -> tuple[list[tuple[str, list[tuple[int, str]]]], bool]:
    """The thread's blocks, each its kind and messages, consecutive agent messages making one answer; whether it ends on one."""
    grouped, joining = [], False
    for message_id, kind, content in messages:
        if kind == "assistant" and joining:
            grouped[-1][1].append((message_id, content))
        elif kind in ("user", "assistant", "report", "limit"):
            grouped.append((kind, [(message_id, content)]))
        # Why: tool calls show in the sidebar; in the thread they just end the answer being joined.
        if kind in ("user", "assistant", "report", "limit", "tool_use", "tool_result"):
            joining = kind == "assistant"
    return grouped, joining


def thread(
    conv_id: str,
    messages: list[tuple[int, str, str]],
    after: int = 0,
    question: int | None = None,
    actions_before: int = 0,
    rendered: dict | None = None,
) -> dict:
    """The blocks holding a message after `after` and the pills of the tool calls answered after it, from a turn's start."""
    grouped, joining = grouping(messages)
    place = {message_id: index for index, (_, parts) in enumerate(grouped) for message_id, _ in parts}
    # Why: a tool call is referenced under the answer before it; those made before a turn's first answer go under
    # that one, unless later calls already did.
    actions, references, answer, waiting, unplaced = [], {}, None, [], []
    for message_id, kind, content in messages:
        if kind in ("user", "assistant"):
            if answer is not None and not references.get(answer):
                references[answer] = unplaced
            if answer is not None or kind == "user":
                unplaced = []
            # Why: a call left unanswered by a turn cut short is not answered by a result of the next.
            if kind == "user":
                waiting = []
            answer = place[message_id] if kind == "assistant" else None
        elif kind == "tool_use":
            waiting.append((message_id, content))
        elif kind == "tool_result" and waiting:
            action = conversation_actions.pill(
                conv_id, actions_before + len(actions) + 1, waiting.pop(0), (message_id, content)
            )
            actions.append(action)
            unplaced = [*unplaced, action]
            if answer is not None:
                references[answer] = [*references.get(answer, []), action]
    if answer is not None and not references.get(answer):
        references[answer] = unplaced
    # Why: a section that is all its turn says has no link of its own; that is read on the answers of the whole turn.
    alone, speaking = set(), []
    for index, (kind, parts) in enumerate([*grouped, ("user", [])]):
        if kind == "user":
            alone.update(speaking * (len(speaking) == 1))
            speaking = []
        elif kind == "assistant" and "".join(content for _, content in parts).strip():
            speaking.append(index)
    # Why: `rendered` is left holding what this reading used and nothing else, for the next to find it there.
    known, rendered = dict(rendered or {}), {} if rendered is None else rendered
    rendered.clear()
    found, last = [], None
    for index, (kind, parts) in enumerate(grouped):
        # Why: the answer a running turn ends on may still grow, and is not yet the turn's final one.
        partial = question is not None and joining and index == len(grouped) - 1
        key = (kind, tuple(parts), partial, index in alone)
        shown = {"kind": kind, "ids": [message_id for message_id, _ in parts], "partial": partial}
        # Why: the page asks again the last question of its thread; it reads it here, as it was sent.
        if kind == "user":
            shown["question"] = parts[0][1]
        # Why: a block is read whole, so one that `after` cuts is given again from its first message.
        if parts[-1][0] > after:
            rendered[key] = known.get(key) or block(conv_id, kind, parts, partial, index in alone)
            shown |= rendered[key]
            shown["references"] = [reference(action) for action in references.get(index, [])]
            found.append(shown)
        elif kind == "assistant":
            shown["report"] = bool(re.match(r"---\n.*?\n---\n", "".join(content for _, content in parts), re.S))
        if kind == "assistant" and not shown.get("report"):
            last = shown
        elif kind == "user" and last:
            last["final"], last = True, None
    if last and question is None:
        last["final"] = True
    pills = [action for action in actions if action["message"] > after]
    return {"blocks": found, "pills": pills}


def finished(conv_id: str, running: bool) -> tuple[list[tuple[int, str, str]], int]:
    """The messages of a conversation's finished turns, and the id of the last of them."""
    messages = store.get_thread_messages(conv_id)
    # Why: the text of the running turn's messages still changes; the stream brings them, from the question on.
    question = max((message_id for message_id, kind, _ in messages if kind == "user"), default=1) if running else None
    last_id = question - 1 if running else max((message_id for message_id, _, _ in messages), default=0)
    return [message for message in messages if message[0] <= last_id], last_id


def output(conv_id: str, running: bool) -> dict:
    """The finished turns of a conversation and their pills, and the message its stream resumes after."""
    messages, last_id = finished(conv_id, running)
    return {**thread(conv_id, messages), "last_id": last_id}


def progress(messages: list[tuple[int, str, str]]) -> str:
    """What the agent is doing, from the last message that says it: a tool call, an answer, an API call retried."""
    for _, kind, content in reversed(messages):
        if kind == "assistant":
            return "Appel modèle · génération de la réponse"
        read = conversation_actions.stored(content, {}) if kind in ("tool_use", "system") else {}
        if kind == "tool_use" and read.get("tool"):
            return f"Outil · {read['tool']}"
        if read.get("subtype") == "api_retry":
            status = f" · dernier statut {read['error_status']}" if read.get("error_status") not in (None, "") else ""
            tries = f"{read.get('attempt', '?')}/{read.get('max_retries', '?')}"
            return f"Appel API · tentative {tries}{status} · {read.get('error') or 'erreur'}"
        if kind == "user":
            break
    return ""


class Live:
    """A conversation as a stream follows it: at each look, the blocks and pills that changed since the last one."""

    def __init__(self, conv_id: str, after: int):
        self.conv_id, self.after = conv_id, after
        kinds = store.get_message_kinds(conv_id)
        reached = min((message_id for message_id, _ in kinds if message_id > after), default=after)
        # Why: read from the start of the turn the page lacks a part of; what a block shows depends on its whole turn.
        self.start = max(
            (message_id for message_id, kind in kinds if kind == "user" and message_id <= reached), default=0
        )
        self.actions_before, waiting = 0, 0
        for message_id, kind in kinds:
            if message_id >= self.start:
                break
            if kind == "user":
                waiting = 0
            elif kind == "tool_use":
                waiting += 1
            elif kind == "tool_result" and waiting:
                waiting, self.actions_before = waiting - 1, self.actions_before + 1
        self.rendered, self.sent, self.cited, self.pills_sent, self.status = {}, None, {}, 0, ""

    def look(self, running: bool) -> dict | None:
        """What to put in the page now: blocks and references that changed, new pills, progress; None if all is as it was."""
        messages = store.get_thread_messages(self.conv_id, self.start)
        question = (
            max((message_id for message_id, kind, _ in messages if kind == "user"), default=0) if running else None
        )
        shown = thread(self.conv_id, messages, self.after, question, self.actions_before, self.rendered)
        marks = [(block["ids"], block["html"], block.get("final"), block["partial"]) for block in shown["blocks"]]
        first_look, known = self.sent is None, self.sent or []
        changed = [block for n, block in enumerate(shown["blocks"]) if n >= len(known) or known[n] != marks[n]]
        # Why: a reference comes under an answer long after it; sent apart, it leaves in place what the page drew there.
        cited = {block["ids"][0]: Markup().join(block["references"]) for block in shown["blocks"]}
        references = {
            first: html
            for first, html in cited.items()
            if html != self.cited.get(first, "") or (html and any(block["ids"][0] == first for block in changed))
        }
        pills = [pill for pill in shown["pills"] if pill["index"] > self.pills_sent]
        self.sent, self.cited = marks, cited
        self.pills_sent = max([self.pills_sent, *(pill["index"] for pill in pills)])
        status, said = progress(messages) if running else "", self.status
        self.status = status
        if not (first_look or pills or changed or references or status != said):
            return None
        settled = question - 1 if question else max((message_id for message_id, _, _ in messages), default=self.after)
        return {
            "blocks": [{**block, "references": []} for block in changed],
            "references": references,
            "pills": pills,
            "settled": max(settled, self.after) if not running else settled,
            "running": running,
            "status": status,
        }
