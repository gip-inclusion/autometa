"""Ce qu'un permalien collé dans Slack montre de sa cible : début de réponse, section, tableau ou graphique."""

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


def read(markdown: str) -> tuple[list[str], list[tuple[int, str, int]]]:
    """Un Markdown en lignes lisibles, sans code ni boutons d'options, et ses tableaux et graphiques là où ils tombent."""
    lines, figures, in_table, bullet = [], [], False, ""
    for token in ANSWER.parse(markdown):
        mermaid = token.type == "fence" and token.info.split()[:1] == ["mermaid"]
        if token.type in ("table_open", "table_close"):
            in_table = token.type == "table_open"
        if token.type == "table_open" or mermaid:
            figures.append((sum(len(line) + 1 for line in lines), "chart" if mermaid else "table", token.map[0]))
        if token.type in ("table_open", "fence", "code_block"):
            bullet = ""
        elif token.type == "list_item_open":
            bullet = "• "
        elif token.type == "inline" and not in_table:
            lines.append(bullet + inline_text(token))
            bullet = ""
    return [line for line in lines if line.strip("• ")], figures


def shortened(text: str, limit: int) -> str:
    """Le texte sans caractère de sens d'écriture, coupé après un mot et suivi de « … » s'il dépasse `limit`."""
    text = BIDI.sub("", text)
    if len(text) <= limit:
        return text
    return f"{text[:limit].rsplit(None, 1)[0]} …"


def text_block(title: str, text: str) -> list[dict]:
    """Un titre et un texte déjà lisibles en un bloc plain_text, que Slack ne lit pas ; aucun s'ils sont vides."""
    shown = "\n".join(part for part in (shortened(title, 150), text) if part)
    return [{"type": "section", "text": {"type": "plain_text", "text": shown, "emoji": False}}] if shown else []


def chart_block(anchor: permalinks.Anchor) -> dict:
    """Un graphique à montrer : l'écoute Slack en fait une image s'il est déposé, sinon sa mention."""
    return {"type": "chart", "source": anchor.text, "title": shortened(anchor.title, 150)}


def text_blocks(title: str, markdown: str) -> list[dict]:
    """Un extrait de texte : le titre, le début du texte, puis le premier tableau ou graphique de ce début."""
    # Why: seul le début est lu ; une réponse entière ferait travailler l'analyseur pour 500 caractères montrés.
    lines, figures = read(markdown[:4000])
    blocks = text_block(title, shortened("\n".join(lines), 500))
    place, kind, line = next(iter(figures), (501, "", 0))
    if place <= 500:
        # Why: lu sur plus long que le texte montré, pour que le compte des lignes laissées d'un tableau soit juste.
        sliced = (a for a in permalinks.anchors(markdown[:50_000]) if a.kind == kind and a.start == line)
        anchor = next(sliced, None)
        if anchor:
            blocks += table_blocks(anchor, titled=False) if kind == "table" else [chart_block(anchor)]
    return blocks


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


def left_note(rows: int, columns: int) -> list[dict]:
    """Ce qu'un tableau montré laisse de côté, en une ligne sous lui ; rien s'il est entier."""
    left = [
        f"{count} {name}{'s' if count > 1 else ''}"
        for count, name in ((rows, "ligne"), (columns, "colonne"))
        if count > 0
    ]
    if not left:
        return []
    return [{"type": "context", "elements": [{"type": "plain_text", "text": f"… {' et '.join(left)} de plus"}]}]


def ascii_table(rows: list[list[str]], lines: int) -> list[dict]:
    """Un tableau en chasse fixe : 10 lignes, des colonnes sur 72 caractères au plus, et ce qui a été laissé."""
    rows = [[cell if len(cell) <= 24 else f"{cell[:23]}…" for cell in row] for row in rows[:11]]
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
    return [
        {"type": "section", "text": {"type": "mrkdwn", "verbatim": True, "text": f"```\n{table}\n```"}},
        *left_note(lines - len(drawn), len(widths) - kept),
    ]


NUMBER = re.compile(r"[-+−]?\d[\d\s.,]*\s*[%€]?")


def slack_table(rows: list[list[str]], lines: int) -> list[dict]:
    """Un tableau en bloc table de Slack : 20 lignes et 20 colonnes au plus, cellules en texte brut, nombres à droite."""
    # Why: Slack lit « <!channel> » et « @here » dans du texte ; une espace sans largeur après « < » et « @ » les
    # laisse lisibles et sans effet, sa documentation ne disant pas qu'une cellule raw_text n'est pas lue.
    cells = [[re.sub(r"([<@])", "\\1\u200b", shortened(cell, 80)) or " " for cell in row[:20]] for row in rows[:21]]
    # Why: Slack refuse un tableau de plus de 10 000 caractères, toutes cellules réunies.
    while sum(len(cell) for row in cells for cell in row) > 9000:
        cells.pop()
    numeric = [
        len(cells) > 1 and all(NUMBER.fullmatch(row[column]) or not row[column].strip() for row in cells[1:])
        for column in range(len(cells[0]))
    ]
    return [
        {
            "type": "table",
            "column_settings": [{"align": "right"} if number else {"is_wrapped": True} for number in numeric],
            "rows": [[{"type": "raw_text", "text": cell} for cell in row] for row in cells],
        },
        *left_note(lines - 1 - len(cells), len(rows[0]) - len(cells[0])),
    ]


def table_blocks(anchor: permalinks.Anchor, titled: bool = True) -> list[dict]:
    """Un tableau sous son titre, en bloc table de Slack et en chasse fixe : l'écoute pose l'un, sinon l'autre."""
    lines = anchor.text.split("\n")
    # Why: seules les premières lignes sont lues, et 1 000 caractères de chacune : une cellule démesurée occuperait
    # l'analyseur, donc le serveur, pendant des secondes.
    rows = table_rows("\n".join(line[:1000] for line in lines[:22]))
    title = anchor.title if titled else ""
    if not rows:
        return text_block(title, shortened("\n".join(read(anchor.text[:4000])[0]), 500))
    return [
        *text_block(title, ""),
        {"type": "table_excerpt", "native": slack_table(rows, len(lines)), "ascii": ascii_table(rows, len(lines))},
    ]


def with_tables(blocks: list[dict], native: bool) -> list[dict]:
    """Les blocs tels que Slack les reçoit, chaque tableau en bloc table ou, à défaut, en chasse fixe."""
    return [
        shown
        for block in blocks
        for shown in (block["native" if native else "ascii"] if block["type"] == "table_excerpt" else [block])
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
        return [chart_block(anchor)]
    # Why: la page entoure une section jusqu'au titre suivant de la réponse jointe, au-delà du message de son titre.
    tokens = ANSWER.parse(text)
    line = first + anchor.start - joined[: len(joined) - len(text)].count("\n")
    heading = next(i for i, token in enumerate(tokens) if token.type == "heading_open" and token.map[0] == line)
    lines = text.replace("\r\n", "\n").split("\n")
    return text_blocks(anchor.title, "\n".join(lines[tokens[heading].map[1] : section_end(tokens, heading)]))
