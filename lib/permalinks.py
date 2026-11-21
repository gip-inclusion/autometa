"""Permalinks into a conversation: the sections and figures of a message, and the one a link names."""

import hashlib
import re
from collections import Counter
from dataclasses import dataclass

__all__ = ["ANCHOR_NAME", "Anchor", "anchors", "resolve"]

# Why: the element part of a permalink; anything else in its place is dropped, never echoed into an address.
ANCHOR_NAME = re.compile(r"(section|table|chart)-(\d{1,6})-([0-9a-f]{6})")


@dataclass(frozen=True)
class Anchor:
    kind: str
    rank: int
    digest: str
    text: str
    title: str
    level: int
    witness: str


def plain(markdown: str) -> str:
    """Inline Markdown as plain text: a link gives its text, emphasis markers and backticks go."""
    linked = re.sub(r"!?\[([^\[\]]*)\]\([^()]*\)", r"\1", markdown)
    # Why: (?<!_) starts a run of underscores at its first one only; tried from each, a long run is quadratic.
    return re.sub(r"[*`]+|(?<!\w)_+|(?<!_)_+(?!\w)", "", linked).strip()


def letters(text: str) -> str:
    """The letters and digits of a text, in order."""
    return "".join(filter(str.isalnum, text))


def anchors(text: str) -> list[Anchor]:
    """The sections, tables and Mermaid charts of a message in reading order, each ranked among its kind and titled."""
    lines = text.replace("\r\n", "\n").split("\n")
    spans, unclosed, section, i = [], [], (0, ""), 0
    while i < len(lines):
        # Why: as in CommonMark, backticks followed by another backtick on their line open inline code, not a fence.
        fence = re.match(r" {0,3}(`{3,}(?=[^`]*$)|~{3,})(.*)", lines[i])
        atx = re.match(r" {0,3}(#{1,6})[ \t]+(\S.*)", lines[i])
        if fence:
            end = next(
                (
                    j
                    for j in range(i + 1, len(lines))
                    if (closer := re.fullmatch(r" {0,3}(`+|~+)[ \t]*", lines[j])) and closer[1].startswith(fence[1])
                ),
                len(lines),
            )
            if fence[2].split()[:1] == ["mermaid"]:
                spans.append(["chart", i + 1, end, *section])
            i = end + 1
        elif atx:
            words = atx[2].strip()
            closed = words.rstrip("#")
            # Why: trailing hashes close a heading only after a space, so a title like C# keeps its own.
            section = (len(atx[1]), plain(closed if not closed or closed[-1] in " \t" else words))
            while unclosed and unclosed[-1][3] >= section[0]:
                unclosed.pop()[2] = i
            unclosed.append(["section", i, len(lines), *section])
            spans.append(unclosed[-1])
            i += 1
        elif (
            "|" in lines[i]
            and i + 1 < len(lines)
            and "|" in lines[i + 1]
            and re.fullmatch(r"[\s|:]*-[\s|:-]*", lines[i + 1])
        ):
            # Why: as in marked, a table ends at a blank line or at a line opening another block: a heading, a fence,
            # a blockquote, a list item able to interrupt a paragraph, a thematic break.
            end = next(
                (
                    j
                    for j in range(i + 2, len(lines))
                    if not lines[j].strip()
                    or re.match(
                        r" {0,3}(?:#{1,6}\s|`{3}|~{3}|>|[*+-] |1[.)] |([-*_])[ \t]*(?:\1[ \t]*){2,}$)", lines[j]
                    )
                ),
                len(lines),
            )
            spans.append(["table", i, end, *section])
            i = end
        else:
            i += 1
    ranks, found = Counter(), []
    for kind, start, end, depth, heading in spans:
        ranks[kind] += 1
        body = "\n".join(lines[start:end]).strip()
        title = heading
        # Why: the page checks each pairing against what it rendered. Letters and digits mostly read alike on both
        # sides; entities, images, reference links or inline HTML make them differ, and the answer then keeps only
        # its own link.
        if kind == "table":
            header = re.sub(r"^\||(?<!\\)\|$", "", lines[start].strip())
            cells = re.split(r"(?<!\\)\|", header)
            witness = f"{len(cells)}x{end - start - 2}:{letters(plain(header))[:40]}"
        elif kind == "chart":
            source = letters(body)
            witness = f"{len(source)}:{source[:40]}"
        else:
            witness = letters(heading)[:40]
        if kind != "section":
            native = kind == "chart" and re.search(
                r"^[ \t]*(?:pie[ \t]+(?:showData[ \t]+)?)?title:?[ \t]+(.+)$", body, re.M
            )
            above = next(
                (lines[j].strip() for j in range(start - (kind == "chart") - 1, -1, -1) if lines[j].strip()), ""
            )
            bold = re.fullmatch(r"\*\*(.+?)\*\*\s*:?", above)
            # Why: a figure is quoted alone; its own title, or the bold line above it, says more than its section.
            title = (native and native[1].strip().strip('"')) or (bold and plain(bold[1])) or heading
        digest = hashlib.sha256(body.encode()).hexdigest()[:6]
        found.append(Anchor(kind, ranks[kind], digest, body, title, depth + (kind != "section"), witness))
    return found


def resolve(found: list[Anchor], kind: str, rank: int, digest: str) -> Anchor | None:
    """The anchor a link names: the one at that rank if its text still matches, else the same text elsewhere."""
    same = [a for a in found if a.kind == kind and a.digest == digest]
    return next((a for a in same if a.rank == rank), same[0] if same else None)
