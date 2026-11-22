"""Ce qu'un permalien collé dans Slack montre de sa cible : début de réponse, section, tableau, mention de graphique."""

import logging
import re

from lib import permalinks
from lib.answer_html import ANSWER
from web import conversation_html
from web.stores.records import Conversation

logger = logging.getLogger(__name__)

# Why: les caractères de sens d'écriture (U+202A à U+202E, U+2066 à U+2069) feraient lire un texte autrement qu'écrit.
BIDI = re.compile("[\u202a-\u202e\u2066-\u2069]")


def inline_text(token) -> str:
    """Le texte d'une ligne de Markdown lue : ni marques d'emphase, ni adresse de lien, ni balise."""
    words = [
        " " if child.type in ("softbreak", "hardbreak", "html_inline") else child.content
        for child in token.children or []
    ]
    return " ".join("".join(words).split())


def plain_text(markdown: str) -> str:
    """Un Markdown en texte lisible, une ligne par paragraphe, titre ou élément de liste ; ses figures sont nommées."""
    lines, in_table, bullet = [], False, ""
    for token in ANSWER.parse(markdown):
        if token.type in ("table_open", "table_close"):
            in_table = token.type == "table_open"
            if in_table:
                lines.append(f"{bullet}(tableau)")
                bullet = ""
        elif in_table:
            continue
        elif token.type == "list_item_open":
            bullet = "• "
        elif token.type == "inline":
            lines.append(bullet + inline_text(token))
            bullet = ""
        elif token.type in ("fence", "code_block"):
            lines.append(bullet + ("(graphique)" if token.info.split()[:1] == ["mermaid"] else "(code)"))
            bullet = ""
    return "\n".join(line for line in lines if line.strip("• "))


def shortened(text: str, limit: int) -> str:
    """Le texte sans caractère de sens d'écriture, coupé après un mot et suivi de « … » s'il dépasse `limit`."""
    text = BIDI.sub("", text)
    if len(text) <= limit:
        return text
    return f"{text[:limit].rsplit(None, 1)[0]} …"


def text_blocks(title: str, markdown: str) -> list[dict]:
    """Un extrait de texte : le titre s'il y en a un, puis le début du texte, en plain_text que Slack ne lit pas."""
    # Why: seul le début est lu ; une réponse entière ferait travailler l'analyseur pour 500 caractères montrés.
    body = shortened(plain_text(markdown[:4000]), 500)
    shown = "\n".join(part for part in (shortened(title, 150), body) if part)
    return [{"type": "section", "text": {"type": "plain_text", "text": shown, "emoji": False}}] if shown else []


def table_rows(markdown: str) -> list[list[str]]:
    """Les lignes du premier tableau lu, cellule par cellule ; aucune si l'une n'a pas autant de cellules que l'en-tête."""
    rows = []
    for token in ANSWER.parse(markdown):
        if token.type == "tr_open":
            rows.append([])
        elif token.type == "inline" and rows:
            rows[-1].append(inline_text(token))
        elif token.type == "table_close":
            break
    return rows if all(len(row) == len(rows[0]) for row in rows) else []


def code_safe(text: str) -> str:
    """Le texte tel qu'un bloc de code Slack l'affiche sans le lire : ni balise, ni accent grave qui le fermerait."""
    text = BIDI.sub("", text)
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace("`", "ˋ")


def table_blocks(anchor: permalinks.Anchor) -> list[dict]:
    """Un tableau en chasse fixe : 10 lignes, des colonnes sur 72 caractères au plus, et ce qui a été laissé."""
    lines = anchor.text.split("\n")
    # Why: seules les premières lignes sont lues, et 1 000 caractères de chacune : une cellule démesurée occuperait
    # l'analyseur, donc le serveur, pendant des secondes.
    rows = table_rows("\n".join(line[:1000] for line in lines[:12]))
    if not rows:
        return text_blocks(anchor.title, anchor.text)
    rows = [[cell if len(cell) <= 24 else f"{cell[:23]}…" for cell in row] for row in rows]
    widths = [max(len(row[column]) for row in rows) for column in range(len(rows[0]))]
    kept = 1
    while kept < len(widths) and sum(widths[: kept + 1]) + 3 * kept <= 72:
        kept += 1
    drawn = [" | ".join(cell.ljust(widths[i]) for i, cell in enumerate(row[:kept])).rstrip() for row in rows]
    drawn.insert(1, "-+-".join("-" * width for width in widths[:kept]))
    table = code_safe("\n".join(drawn))
    # Why: échappés, « & », « < » et « > » comptent quatre ou cinq caractères ; Slack refuse un texte de plus de 3 000.
    while len(table) > 2900:
        drawn.pop()
        table = code_safe("\n".join(drawn))
    left = [
        f"{count} {name}{'s' if count > 1 else ''}"
        for count, name in ((len(lines) - len(drawn), "ligne"), (len(widths) - kept, "colonne"))
        if count > 0
    ]
    return [
        *text_blocks(anchor.title, ""),
        {"type": "section", "text": {"type": "mrkdwn", "verbatim": True, "text": f"```\n{table}\n```"}},
        *(
            [{"type": "context", "elements": [{"type": "plain_text", "text": f"… {' et '.join(left)} de plus"}]}]
            if left
            else []
        ),
    ]


def section_end(tokens, heading: int) -> int | None:
    """La ligne où finit la section d'un titre : au titre suivant de son rang ou au-dessus, comme la page l'entoure."""
    opened, closed = tokens[heading], False
    for token in tokens[heading + 3 :]:
        # Why: un titre dans une liste ou une citation n'a de suite que dans celle-ci ; sa section finit avec elle.
        closed = closed or token.level < opened.level
        if closed or (token.type == "heading_open" and token.level == opened.level and token.tag <= opened.tag):
            if token.map:
                return token.map[0]
            closed = True
    return None


def excerpt(conv: Conversation, message_id: int | None, anchor_name: str | None) -> list[dict]:
    """Les blocs Slack de ce que désigne un permalien, comme la page le résout ; aucun pour la conversation seule."""
    parts = message_id and conversation_html.finished_answer(conv.id, conv.needs_response, message_id)
    if not parts:
        return []
    joined = "".join(content for _, content in parts)
    text = re.sub(r"\A---\n.*?\n---\n", "", joined, flags=re.S)
    named = permalinks.ANCHOR_NAME.fullmatch(anchor_name or "")
    if not named:
        return text_blocks("", text)
    # Why: désigner un élément demande de rendre toute la réponse ; au-delà, des secondes de calcul dans le serveur.
    if len(joined) > 300_000:
        logger.info("Réponse %s de la conversation %s trop longue pour un extrait d'élément", message_id, conv.id)
        return []
    kind, rank, digest = named.groups()
    # Why: la page ne pose un lien que là où le découpage, l'analyseur et le nettoyage du HTML laissent un élément ;
    # son rendu fait foi, et tout autre nom mène à la réponse entière, comme sur la page.
    html = conversation_html.answer_block(conv.id, parts)["html"]
    same = [
        (anchor, first)
        for holder, first, anchor in conversation_html.answer_anchors(parts)
        if holder == message_id
        and anchor.kind == kind
        and anchor.digest == digest
        and f'data-anchor="{holder}-{kind}-{anchor.rank}"' in html
    ]
    # Why: comme sur la page, un élément déplacé par une modification garde son empreinte : elle le désigne encore.
    anchor, first = next((found for found in same if found[0].rank == int(rank)), same[0] if same else (None, 0))
    if not anchor:
        return text_blocks("", text)
    if kind == "table":
        return table_blocks(anchor)
    if kind == "chart":
        return text_blocks(f"Graphique : {anchor.title}" if anchor.title else "Graphique", "")
    # Why: la page entoure une section jusqu'au titre suivant de la réponse jointe, au-delà du message de son titre.
    tokens = ANSWER.parse(text)
    line = first + anchor.start - joined[: len(joined) - len(text)].count("\n")
    heading = next(i for i, token in enumerate(tokens) if token.type == "heading_open" and token.map[0] == line)
    lines = text.replace("\r\n", "\n").split("\n")
    return text_blocks(anchor.title, "\n".join(lines[tokens[heading].map[1] : section_end(tokens, heading)]))
