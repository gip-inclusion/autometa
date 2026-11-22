"""A conversation's finished turns as the HTML of its page: questions, answers, report cards and limit notices."""

import json
import re
from decimal import ROUND_HALF_UP, Decimal

from markupsafe import Markup

from lib import permalinks
from lib.answer_html import Link, render_answer, render_user
from web.database import store

# What web/uploads.py writes into a question for each attached file, with the file's text when it is short.
FILE_BLOCK = re.compile(r"\[Uploaded file: ([^\]]+)\]\n(?:- [^\n]+\n)+(?:```[\s\S]*?```\n?)?")


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


def file_pill(block: re.Match) -> Markup:
    size = re.search(r"- Size: ([0-9,]+) bytes", block[0])
    mime = (re.search(r"- Type: ([^\n]+)", block[0]) or ["", ""])[1]
    shown = size and Markup(' <span class="file-context-size">({})</span>').format(
        file_size(int(size[1].replace(",", "")))
    )
    return Markup('<span class="file-context-pill" title="{}"><i class="{}"></i> {}{}</span>').format(
        mime, file_icon(mime), block[1], shown or ""
    )


def user_html(content: str) -> Markup:
    """A question: its attached files as pills, then its text."""
    pills = [file_pill(block) for block in FILE_BLOCK.finditer(content)]
    text = content
    if pills:
        text = re.sub(r"^\s*---\n", "", FILE_BLOCK.sub("", content)).strip()
    shown = Markup('<div class="user-text">{}</div>').format(Markup(render_user(text))) if text or not pills else ""
    if not pills:
        return shown
    return Markup('<div class="file-context-pills">{}</div>{}').format(Markup().join(pills), shown)


def permalink_button(url: str, label: str) -> Markup:
    return Markup(
        '<button type="button" class="permalink-btn" data-url="{0}" title="Copier le lien vers {1}" '
        'aria-label="Copier le lien vers {1}"><i class="ri-link" aria-hidden="true"></i></button>'
    ).format(url, label)


def element_links(conv_id: str, parts: list[tuple[int, str]], skipped: int) -> tuple[Link, ...]:
    """The link of each section, table and chart of an answer, at its line in the text once its messages are joined."""
    links, line, glued = [], -skipped, False
    labels = {"section": "cette section", "table": "ce tableau", "chart": "ce graphique"}
    for message_id, content in parts:
        content = content.replace("\r\n", "\n")
        # Why: a lone carriage return is a line break for the renderer and not for the slicer; lines would not agree.
        if "\r" in content:
            return ()
        for anchor in permalinks.anchors(content):
            # Why: joined to a message that does not end its last line, a first line starts no element.
            if anchor.start == 0 and glued:
                continue
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
        line += content.count("\n")
        if content:
            glued = not content.endswith("\n")
    return tuple(links)


def report_header(text: str, front_matter: str) -> Markup:
    """The header of an answer that opens with front matter: its category, date, site and the report file it names."""
    fields = {}
    for line in front_matter.split("\n"):
        # Why: the page's JavaScript reads names in ASCII, and a value up to any of its line terminators.
        if field := re.fullmatch(r"([A-Za-z0-9_][A-Za-z0-9_\s]*?):\s*([^\n\r\u2028\u2029]+)", line):
            fields[field[1].strip()] = field[2].strip()
    header = Markup('<div class="report-title"><i class="ri-file-text-line"></i> {}</div>').format(
        fields.get("query category") or "Rapport"
    )
    for name, icon in (("date", "ri-calendar-line"), ("website", "ri-global-line")):
        if fields.get(name):
            header += Markup('<div class="report-meta"><i class="{}"></i> {}</div>').format(icon, fields[name])
    if filename := re.search(r"[0-9]{4}-[0-9]{2}-[A-Za-z0-9_-]+\.md", text):
        header += Markup(
            '<a href="/api/reports/{}" target="_blank" class="report-link">'
            '<i class="ri-external-link-line"></i> Voir le rapport complet</a>'
        ).format(filename[0])
    return Markup('<div class="report-header">{}</div>').format(header)


def answer_block(conv_id: str, parts: list[tuple[int, str]]) -> dict:
    """An answer: consecutive agent messages read as one text, as the page joins them."""
    text = "".join(content for _, content in parts)
    front_matter = re.match(r"---\n(.*?)\n---\n", text, re.S)
    start = front_matter.end() if front_matter else 0
    body = Markup(render_answer(text[start:], element_links(conv_id, parts, text[:start].count("\n"))))
    if front_matter:
        body = report_header(text, front_matter[1]) + Markup('<div class="report-body">{}</div>').format(body)
    link = permalink_button(f"/c/{conv_id}/{parts[0][0]}", "cette réponse")
    return {
        "kind": "assistant",
        "ids": [message_id for message_id, _ in parts],
        "report": bool(front_matter),
        "html": link + body,
    }


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


def blocks(conv_id: str, messages: list[tuple[int, str, str]]) -> list[dict]:
    """The blocks of the thread, in order; the last answer of each turn is marked final unless it is a report."""
    found, answer = [], None
    for message_id, kind, content in messages:
        if kind == "assistant":
            if answer is None:
                answer = []
                found.append(answer)
            answer.append((message_id, content))
        # Why: the page reads tool calls for its sidebar only; in the thread they just end the answer being joined.
        elif kind in ("user", "report", "limit", "tool_use", "tool_result"):
            answer = None
        if kind == "user":
            found.append({"kind": kind, "ids": [message_id], "html": user_html(content)})
        elif kind == "report":
            found.append({"kind": kind, "ids": [message_id], "html": report_card(content)})
        elif kind == "limit":
            notice = Markup('<i class="ri-time-line" aria-hidden="true"></i><div>{}</div>').format(content)
            found.append({"kind": kind, "ids": [message_id], "html": notice})
    found = [answer_block(conv_id, block) if isinstance(block, list) else block for block in found]
    last = None
    for block in [*found, {"kind": "user"}]:
        if block["kind"] == "assistant" and not block["report"]:
            last = block
        elif block["kind"] == "user" and last:
            last["final"], last = True, None
    return found


def output(conv_id: str, running: bool, after: int = 0) -> dict:
    """The finished turns of a conversation after message `after`, and the message its stream resumes from."""
    messages = store.get_displayed_messages(conv_id, ("user", "assistant", "report", "limit"))
    # Why: the text of the running turn's messages still changes; the stream draws them, from the question on.
    question = max((message_id for message_id, kind, _ in messages if kind == "user"), default=1) if running else None
    last_id = question - 1 if running else max((message_id for message_id, _, _ in messages), default=0)
    shown = [message for message in messages if after < message[0] <= last_id]
    return {"blocks": blocks(conv_id, shown), "last_id": last_id, "running": running}
