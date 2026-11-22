"""Ce qu'un permalien collé dans Slack montre de sa cible : début de réponse, section, tableau, mention de graphique."""

import re

from lib import permalinks
from lib.answer_html import ANSWER
from web import conversation_html
from web.stores.records import Conversation


def inline_text(token) -> str:
    """Le texte d'une ligne de Markdown lue : ni marques d'emphase, ni adresse de lien, ni balise."""
    words = [
        " " if child.type in ("softbreak", "hardbreak") else child.content
        for child in token.children or []
        if child.type != "html_inline"
    ]
    return " ".join("".join(words).split())


def plain_text(markdown: str) -> str:
    """Un Markdown en texte lisible, une ligne par paragraphe, titre ou élément de liste ; ses figures sont nommées."""
    lines, in_table, bullet = [], False, ""
    for token in ANSWER.parse(markdown):
        if token.type in ("table_open", "table_close"):
            in_table = token.type == "table_open"
            if in_table:
                lines.append("(tableau)")
        elif in_table:
            continue
        elif token.type == "list_item_open":
            bullet = "• "
        elif token.type == "inline":
            lines.append(bullet + inline_text(token))
            bullet = ""
        elif token.type in ("fence", "code_block"):
            lines.append("(graphique)" if token.info.split()[:1] == ["mermaid"] else "(code)")
    return "\n".join(line for line in lines if line.strip("• "))


def shortened(text: str, limit: int) -> str:
    """Le texte, coupé après un mot et suivi de « … » s'il dépasse `limit` caractères."""
    if len(text) <= limit:
        return text
    return f"{text[:limit].rsplit(None, 1)[0]} …"


def text_blocks(title: str, markdown: str) -> list[dict]:
    """Un extrait de texte : le titre s'il y en a un, puis le début du texte, en plain_text que Slack ne lit pas."""
    # Why: seul le début est lu ; une réponse entière ferait travailler l'analyseur pour 500 caractères montrés.
    body = shortened(plain_text(markdown[:4000]), 500)
    shown = "\n".join(part for part in (title, body) if part)
    return [{"type": "section", "text": {"type": "plain_text", "text": shown, "emoji": False}}] if shown else []


def table_rows(markdown: str) -> list[list[str]]:
    rows = []
    for token in ANSWER.parse(markdown):
        if token.type == "tr_open":
            rows.append([])
        elif token.type == "inline" and rows:
            rows[-1].append(inline_text(token))
    return rows


def code_safe(text: str) -> str:
    """Le texte tel qu'un bloc de code Slack l'affiche sans le lire : ni balise, ni accent grave qui le fermerait."""
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace("`", "ˋ")


def table_blocks(anchor: permalinks.Anchor) -> list[dict]:
    """Un tableau en chasse fixe : 10 lignes, des colonnes sur 72 caractères au plus, et ce qui a été laissé."""
    lines = anchor.text.split("\n")
    rows = table_rows("\n".join(lines[:12]))
    if not rows:
        return text_blocks(anchor.title, anchor.text)
    rows = [[cell if len(cell) <= 24 else f"{cell[:23]}…" for cell in row] for row in rows]
    widths = [max(len(row[column]) for row in rows) for column in range(len(rows[0]))]
    kept = 1
    while kept < len(widths) and sum(widths[: kept + 1]) + 3 * kept <= 72:
        kept += 1
    drawn = [" | ".join(cell.ljust(widths[i]) for i, cell in enumerate(row[:kept])).rstrip() for row in rows]
    drawn.insert(1, "-+-".join("-" * width for width in widths[:kept]))
    left = [
        f"{count} {name}{'s' if count > 1 else ''}"
        for count, name in ((len(lines) - 12, "ligne"), (len(widths) - kept, "colonne"))
        if count > 0
    ]
    table = "\n".join(drawn)
    return [
        *text_blocks(anchor.title, ""),
        {"type": "section", "text": {"type": "mrkdwn", "verbatim": True, "text": f"```\n{code_safe(table)}\n```"}},
        *(
            [{"type": "context", "elements": [{"type": "plain_text", "text": f"… {' et '.join(left)} de plus"}]}]
            if left
            else []
        ),
    ]


def excerpt(conv: Conversation, message_id: int | None, anchor_name: str | None) -> list[dict]:
    """Les blocs Slack de ce que désigne un permalien, comme la page le résout ; aucun pour la conversation seule."""
    parts = message_id and conversation_html.finished_answer(conv.id, conv.needs_response, message_id)
    if not parts:
        return []
    named = permalinks.ANCHOR_NAME.fullmatch(anchor_name or "")
    if named:
        kind, rank, digest = named.groups()
        same = [
            anchor
            for holder, _, anchor in conversation_html.answer_anchors(parts)
            if holder == message_id and anchor.kind == kind and anchor.digest == digest
        ]
        # Why: comme sur la page, un élément déplacé par une modification garde son empreinte : elle le désigne encore.
        anchor = next((a for a in same if a.rank == int(rank)), same[0] if same else None)
        if anchor and kind == "table":
            return table_blocks(anchor)
        if anchor and kind == "chart":
            return text_blocks(f"Graphique : {anchor.title}" if anchor.title else "Graphique", "")
        if anchor:
            return text_blocks(anchor.title, anchor.text.partition("\n")[2])
    text = "".join(content for _, content in parts)
    return text_blocks("", re.sub(r"\A---\n.*?\n---\n", "", text, flags=re.S))
