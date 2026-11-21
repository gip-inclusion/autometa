"""Permalinks into a conversation: the sections and figures of a message, and the one a link names."""

import hashlib
import re
from collections import Counter
from dataclasses import dataclass

__all__ = ["Anchor", "anchors", "resolve"]


@dataclass(frozen=True)
class Anchor:
    kind: str
    rank: int
    digest: str
    text: str
    title: str
    level: int


def caption(lines: list[str], first: int) -> str:
    """The bold line standing just above a figure, without its markers; empty when there is none."""
    above = next((line.strip() for line in reversed(lines[:first]) if line.strip()), "")
    bold = re.fullmatch(r"\*\*(.+?)\*\*\s*:?", above)
    return bold[1] if bold else ""


def anchors(text: str) -> list[Anchor]:
    """The sections, tables and Mermaid charts of a message in reading order, each ranked among its kind and titled."""
    lines = text.split("\n")
    spans, headings, i = [], [], 0
    while i < len(lines):
        fence = re.match(r" {0,3}(`{3,}|~{3,})\s*(\w*)", lines[i])
        heading = re.match(r" {0,3}(#{1,6})\s+\S", lines[i])
        if fence:
            end = next(
                (
                    j
                    for j in range(i + 1, len(lines))
                    if lines[j].strip().startswith(fence[1]) and set(lines[j].strip()) == {fence[1][0]}
                ),
                len(lines),
            )
            if fence[2] == "mermaid":
                spans.append(("chart", i + 1, end))
            i = end + 1
        elif heading:
            headings.append((len(heading[1]), i))
            i += 1
        elif (
            "|" in lines[i]
            and i + 1 < len(lines)
            and "|" in lines[i + 1]
            and re.fullmatch(r"[\s|:-]*-[\s|:-]*", lines[i + 1])
        ):
            end = next(
                (
                    j
                    for j in range(i + 2, len(lines))
                    if not lines[j].strip() or re.match(r" {0,3}(#{1,6}\s|`{3}|~{3})", lines[j])
                ),
                len(lines),
            )
            spans.append(("table", i, end))
            i = end
        else:
            i += 1
    spans += [
        ("section", start, next((s for other, s in headings if s > start and other <= level), len(lines)))
        for level, start in headings
    ]
    ranks, found = Counter(), []
    for kind, start, end in sorted(spans, key=lambda span: span[1]):
        ranks[kind] += 1
        body = "\n".join(lines[start:end]).strip()
        above = [(level, at) for level, at in headings if at <= start]
        depth, heading = (above[-1][0], lines[above[-1][1]].strip().strip("#").strip()) if above else (0, "")
        native = re.search(r'^\s*title:?\s+"?(.+?)"?\s*$', body, re.M) if kind == "chart" else None
        title = heading
        if kind != "section":
            # Why: a figure is quoted alone; its own title says more than the section it sits in.
            title = (native and native[1]) or caption(lines, start - (kind == "chart")) or heading
        digest = hashlib.sha256(body.encode()).hexdigest()[:6]
        found.append(Anchor(kind, ranks[kind], digest, body, title, depth + (kind != "section")))
    return found


def resolve(found: list[Anchor], kind: str, rank: int, digest: str) -> Anchor | None:
    """The anchor a link names: the one at that rank if its text still matches, else the same text elsewhere."""
    same = [a for a in found if a.kind == kind and a.digest == digest]
    return next((a for a in same if a.rank == rank), same[0] if same else None)
