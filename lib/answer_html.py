"""Conversation Markdown as HTML: markdown-it-py tuned to marked 15.0.12, then nh3 with the page's DOMPurify policy."""

import bisect
import html
import re
import secrets
from collections import defaultdict
from dataclasses import dataclass
from functools import partial
from urllib.parse import quote

import nh3
from markdown_it import MarkdownIt
from markdown_it.common.utils import escapeHtml, isMdAsciiPunct, isPunctChar, isWhiteSpace
from markdown_it.renderer import RendererHTML
from markdown_it.rules_inline.state_inline import Delimiter, Scanned
from markdown_it.token import Token
from mdit_py_plugins.tasklists import tasklists_plugin

__all__ = ["Link", "render_answer", "render_user"]

# marked 15 GFM extended autolinks (inline.url, inline._backpedal) and bare emails.
MARKED_URL = re.compile(r"((?:ftp|https?)://|www\.)(?:[a-zA-Z0-9\-]+\.?)+[^\s<]*", re.I)
# marked leaves these as entities in text, so the browser decodes them, inside a bare URL too.
ENTITY = re.compile(r"&(?:#\d{1,7}|#[Xx][a-fA-F0-9]{1,6}|\w+);")
MARKED_EMAIL = re.compile(r"[A-Za-z0-9._+-]+@[a-zA-Z0-9-_]+(?:\.[a-zA-Z0-9-_]*[a-zA-Z0-9])+(?![-_])")
BACKPEDAL = re.compile(r"(?:[^?!.,:;*_'\"~()&]+|\([^)]*\)|&(?![a-zA-Z0-9]+;$)|[?!.,:;*_'\"~)]+(?!$))+")
# markdown-it's text terminators, plus where marked's text rule stops for an autolink to start.
TEXT_STOP = re.compile(
    r"[\n!#$%&*+\-:<=>@\[\\\]^_`{}~]|(?:https?|ftp)://|www\.|(?<![A-Za-z0-9._+-])" + MARKED_EMAIL.pattern
)


def marked_href(url):
    """marked's cleanUrl: encodeURI, then %25 back to %."""
    return quote(url, safe=";,/?:@&=+$-_.!~*'()#").replace("%25", "%")


def marked_text(state, silent):
    # Why: marked tries a URL before text where a token starts, its pattern ignoring case; its text stops do not.
    if MARKED_URL.match(state.src, state.pos, state.posMax):
        return False
    stop = TEXT_STOP.search(state.src, state.pos, state.posMax)
    end = stop.start() if stop else state.posMax
    if end == state.pos:
        return False
    if not silent:
        state.pending += state.src[state.pos : end]
    state.pos = end
    return True


def marked_url(state, silent):
    # Why: silent is a link label being scanned; marked matches the whole link first, so nothing inside spills past ].
    if silent or state.linkLevel > 0:
        return False
    email = MARKED_EMAIL.match(state.src, state.pos, state.posMax)
    if email:
        text, href = email[0], "mailto:" + email[0]
    else:
        m = MARKED_URL.match(state.src, state.pos, state.posMax)
        if not m:
            return False
        text = m[0]
        while (shorter := (BACKPEDAL.match(text) or [""])[0]) != text:
            text = shorter
        if not text:
            return False
        href = "http://" + text if m[1].lower() == "www." else text
    shown = ENTITY.sub(lambda e: html.unescape(e[0]), text)
    token = state.push("link_open", "a", 1)
    token.attrs = {"href": ENTITY.sub(lambda e: html.unescape(e[0]), state.md.normalizeLink(href))}
    token.markup, token.info = "linkify", "auto"
    state.push("text", "", 0).content = text if email else shown
    state.push("link_close", "a", -1).markup = "linkify"
    state.pos += len(text)
    return True


def marked_scan(state, start, can_split_word):
    """scanDelims, except that marked does not count * and _ as punctuation next to a delimiter run."""
    marker, pos = state.src[start], start
    while pos < state.posMax and state.src[pos] == marker:
        pos += 1
    last = state.src[start - 1] if start > 0 else " "
    nxt = state.src[pos] if pos < state.posMax else " "
    last_punct = last not in "*_" and (isMdAsciiPunct(ord(last)) or isPunctChar(last))
    next_punct = nxt not in "*_" and (isMdAsciiPunct(ord(nxt)) or isPunctChar(nxt))
    last_space, next_space = isWhiteSpace(ord(last)), isWhiteSpace(ord(nxt))
    left = not (next_space or (next_punct and not (last_space or last_punct)))
    right = not (last_space or (last_punct and not (next_space or next_punct)))
    return Scanned(
        left and (can_split_word or not right or last_punct),
        right and (can_split_word or not left or next_punct),
        pos - start,
    )


def marked_emphasis(state, silent):
    marker = state.src[state.pos]
    if silent or marker not in "_*":
        return False
    scanned = marked_scan(state, state.pos, marker == "*")
    for _ in range(scanned.length):
        state.push("text", "", 0).content = marker
        state.delimiters.append(
            Delimiter(ord(marker), scanned.length, len(state.tokens) - 1, -1, scanned.can_open, scanned.can_close)
        )
    state.pos += scanned.length
    return True


def emphasis_limit(state):
    """Where an emphasis opened before this point closes: marked reads a tilde only inside it."""
    pending = []
    for d in state.delimiters:
        if d.marker not in (0x2A, 0x5F):
            continue
        if d.close and any(o.marker == d.marker for o in pending):
            while pending.pop().marker != d.marker:
                pass
        elif d.open:
            pending.append(d)
    limit = state.posMax
    for marker in {d.marker for d in pending}:
        char = chr(marker)
        i = state.src.find(char, state.pos, state.posMax)
        while i != -1 and i < limit:
            if marked_scan(state, i, marker == 0x2A).can_close:
                limit = i
                break
            while i < state.posMax and state.src[i] == char:
                i += 1
            i = state.src.find(char, i, state.posMax)
    return limit


def tilde_closers(src):
    """Tilde runs marked's strikethrough may close on: {start: length}, after a char that may end its text."""
    found = {}
    for run in re.finditer(r"~+", src):
        j, size = run.start(), len(run[0])
        slashes = j - len(src[:j].rstrip("\\"))
        if slashes % 2:
            j, size, last_ok = j + 1, size - 1, True
        elif slashes or j == 0:
            last_ok = slashes > 0
        else:
            escaped = (j - 1 - len(src[: j - 1].rstrip("\\"))) % 2
            last_ok = bool(escaped) or not src[j - 1].isspace()
        if size and last_ok:
            found[j] = size
    exact = {n: [j for j, size in found.items() if size == n] for n in (1, 2)}
    return found, exact


def del_match(state, limit):
    """marked's strikethrough (one or two tildes, matched by a regex) at state.pos, bounded by limit: (start, end)."""
    src, pos = state.src, state.pos
    size = 2 if src.startswith("~~", pos) else 1
    start = pos + size
    if start >= limit or src[start].isspace() or src[start] == "~":
        return None
    if getattr(state, "tilde_src", None) is not src:
        state.tilde_src, state.tilde_closers = src, tilde_closers(src)
    runs, exact = state.tilde_closers
    closers = exact[size]
    i = bisect.bisect_left(closers, start + 1)
    if i < len(closers) and closers[i] + size <= limit:
        return start, closers[i]
    # Why: the limit may cut a longer run, whose head then closes as the regex's $ allows.
    cut = limit - size
    if cut > start and runs.get(cut, 0) > size:
        return start, cut
    return None


def marked_strikethrough(state, silent):
    if silent or state.src[state.pos] != "~":
        return False
    m = del_match(state, emphasis_limit(state))
    if not m:
        # Why: marked's text rule takes a run of tildes and backticks whole, so a backtick after ~ opens no code.
        run = re.match(r"[`~]+", state.src[state.pos : state.posMax])[0]
        state.pending += run
        state.pos += len(run)
        return True
    state.push("del_open", "del", 1)
    old_max = state.posMax
    size = m[0] - state.pos
    state.pos, state.posMax = m
    state.md.inline.tokenize(state)
    state.posMax = old_max
    state.push("del_close", "del", -1)
    state.pos = m[1] + size
    return True


def align_attribute(state):
    """Table cells carry align="…" as marked writes it, not a style the sanitizer drops."""
    for token in state.tokens:
        if token.type in ("th_open", "td_open") and token.attrs.get("style", "").startswith("text-align:"):
            token.attrs = {"align": token.attrs["style"].removeprefix("text-align:")}


# marked ends a list item at a less-indented line opening HTML or starting with #, where CommonMark would continue.
ITEM_BREAK = re.compile(r" {0,3}(?:<(?:[a-z].*>|!--)|#)", re.I)


def marked_item_break(state, start_line, end_line, silent):
    if state.listIndent < 0 or state.sCount[start_line] >= state.blkIndent:
        return False
    line = state.src[state.bMarks[start_line] : state.eMarks[start_line]]
    return bool(ITEM_BREAK.match(line)) and silent


def code_newline(state):
    """Code ends with one newline as in marked: a fence drops the line before its closer, indented code all blanks."""
    for token in state.tokens:
        if token.type == "fence":
            token.content = token.content.removesuffix("\n").removesuffix("\n") + "\n"
        elif token.type == "code_block":
            token.content = token.content.rstrip("\n") + "\n"


def task_checkboxes(state):
    """The checkbox the task-list rule put at the head of an item becomes a token of its own, apart from typed HTML."""
    task = False
    for token in state.tokens:
        if token.type == "list_item_open":
            task = token.attrs.pop("class", None) == "task-list-item"
        elif token.type in ("bullet_list_open", "ordered_list_open"):
            token.attrs.pop("class", None)
        elif token.type == "inline" and task:
            box, task = token.children[0], False
            box.type, box.meta = "task_checkbox", {"checked": 'checked="checked"' in box.content}


CHECKBOX = ['<input disabled="" type="checkbox">', '<input checked="" disabled="" type="checkbox">']


def task_checkbox(renderer, tokens, idx, options, env):
    checked = tokens[idx].meta["checked"]
    # Why: an answer's checkbox goes through the sanitizer as a mark, since no typed <input> may come out of it.
    if "mark" in env:
        return f'<span class="{env["mark"]}c{checked:d}"></span>'
    return CHECKBOX[checked]


def marked_fence(renderer, tokens, idx, options, env):
    """A fence, its <pre> carrying the mark of the permalink that names it."""
    rendered = RendererHTML.fence(renderer, tokens, idx, options, env)
    mark = tokens[idx].meta.get("mark")
    return rendered.replace("<pre>", f'<pre class="{mark}">', 1) if mark else rendered


def build():
    md = MarkdownIt("commonmark", {"breaks": True, "html": True})
    md.enable("table")
    md.use(tasklists_plugin)
    md.inline.ruler.at("text", marked_text)
    md.inline.ruler.at("emphasis", marked_emphasis)
    md.inline.ruler.before("emphasis", "marked_strikethrough", marked_strikethrough)
    md.inline.ruler.before("autolink", "marked_url", marked_url)
    md.block.ruler.before("paragraph", "marked_item_break", marked_item_break, {"alt": ["paragraph"]})
    md.core.ruler.push("align_attribute", align_attribute)
    md.core.ruler.push("code_newline", code_newline)
    md.core.ruler.push("task_checkboxes", task_checkboxes)
    # Why: marked writes <br> with no newline after it, so textContent (TOC labels, titles) glues the lines as it does.
    md.add_render_rule("softbreak", lambda *args: "<br>")
    md.add_render_rule("hardbreak", lambda *args: "<br>")
    md.add_render_rule("task_checkbox", task_checkbox)
    md.add_render_rule("fence", marked_fence)
    md.normalizeLink = marked_href
    md.normalizeLinkText = lambda url: url
    md.validateLink = lambda url: True
    return md


ANSWER = build()

# DOMPurify 3.4.17 USE_PROFILES {html: true} minus the page's FORBID_TAGS, and minus <input>: see task_checkbox.
PURIFY_TAGS = set(
    (
        "a abbr acronym address area article aside audio b bdi bdo big blink blockquote br canvas caption "
        "center cite code col colgroup content data dd decorator del details dfn dir div dl dt "
        "element em figcaption figure font footer h1 h2 h3 h4 h5 h6 header hgroup hr i img ins kbd "
        "li main map mark menu menuitem meter nav nobr ol optgroup p picture pre "
        "progress q rp rt ruby s samp search section shadow slot small source spacer span strike strong sub "
        "summary sup table tbody td template tfoot th thead time tr track tt u ul var video wbr"
    ).split()
)
# DOMPurify html attributes minus FORBID_ATTR ['style', 'id', 'name']; class is filtered separately.
PURIFY_ATTRS = set(
    (
        "accept action align alt autocapitalize autocomplete autopictureinpicture autoplay background bgcolor border "
        "capture cellpadding cellspacing checked cite clear color cols colspan controls controlslist coords "
        "crossorigin datetime decoding default dir disabled disablepictureinpicture disableremoteplayback download "
        "draggable enctype enterkeyhint face for headers height hidden high href hreflang inputmode integrity ismap "
        "kind label lang list loading loop low max maxlength media method min minlength multiple muted nonce noshade "
        "novalidate nowrap open optimum pattern placeholder playsinline "
        "poster preload pubdate radiogroup readonly rel required rev reversed role rows rowspan spellcheck scope "
        "selected shape size sizes span srclang start src srcset step summary tabindex title translate type usemap "
        "valign value width wrap xmlns slot"
    ).split()
)


def keep_attribute(mark, element, attribute, value):
    """Only code keeps a class, only a language- one; data: URIs only as media sources, as DOMPurify does."""
    if attribute == "class":
        language = element == "code" and re.fullmatch(r"language-[\w-]+", value)
        return value if language or value.startswith(mark) else None
    if value[:5].lower() == "data:" and (
        attribute != "src" or element not in ("img", "audio", "video", "source", "track")
    ):
        return None
    return value


def clean(rendered, mark):
    return nh3.clean(
        rendered,
        tags=PURIFY_TAGS,
        attributes={"*": PURIFY_ATTRS | {"class"}},
        attribute_filter=partial(keep_attribute, mark),
        generic_attribute_prefixes={"aria-"},
        url_schemes={"http", "https", "ftp", "ftps", "mailto", "tel", "callto", "sms", "cid", "xmpp", "matrix", "data"},
        link_rel=None,
        strip_comments=True,
    )


@dataclass(frozen=True)
class Link:
    """A section, table or chart the permalink slicer saw from line `start` of the text, and the HTML that links it."""

    kind: str
    start: int
    end: int
    level: int
    attributes: str
    button: str


ELEMENT_TOKENS = {"section": "heading_open", "table": "table_open", "chart": "fence"}


def place_links(tokens, links, mark):
    """The tokens with each link marked on the element parsed at its lines; none where slicer and parser disagree."""
    at = {(t.type, t.map[0]): i for i, t in enumerate(tokens) if t.map and t.type in ELEMENT_TOKENS.values()}
    added = defaultdict(list)
    for n, link in enumerate(links):
        i = at.get((ELEMENT_TOKENS[link.kind], link.start))
        if i is None:
            continue
        token, button = tokens[i], f'<span class="{mark}b{n}"></span>'
        if link.kind == "section":
            if token.markup == "#" * link.level:
                token.attrSet("class", f"{mark}e{n}")
                added[i + 2].append(button)
            continue
        if link.kind == "table":
            if token.map[1] != link.end:
                continue
            token.attrSet("class", f"{mark}e{n}")
            closes = (j for j in range(i, len(tokens)) if tokens[j].type == "table_close")
            last = next(j for j in closes if tokens[j].level == token.level)
        else:
            if token.info.split()[:1] != ["mermaid"]:
                continue
            token.meta["mark"] = f"{mark}e{n}"
            last = i
        added[i].append(f'<div class="{mark}f">')
        added[last + 1].append(f"{button}</div>")
    placed = []
    for i, token in enumerate([*tokens, None]):
        placed += [Token("html_block", "", 0, content=content) for content in added[i]]
        placed.append(token)
    return placed[:-1]


def render_answer(text: str, links: tuple[Link, ...] = ()) -> str:
    """Agent text as the page shows it, sanitized; each link written on its element with its button."""
    # Why: what the app adds goes through the sanitizer under a class no answer can guess, then takes its real form.
    mark = f"m{secrets.token_hex(16)}"
    tokens = place_links(ANSWER.parse(text), links, mark)
    cleaned = clean(ANSWER.renderer.render(tokens, ANSWER.options, {"mark": mark}), mark)

    def written(m):
        kind, n = m[2], int(m[3] or 0)
        if kind == "b":
            return links[n].button
        if kind == "c":
            return CHECKBOX[n]
        return links[n].attributes if kind == "e" else 'class="permalink-figure"'

    return re.sub(rf'(<span )?class="{mark}([bcef])(\d*)"(?(1)></span>)', written, cleaned)


def safe_user_url(url):
    """Whether a link typed by a user may be followed: no control character, a web, mail or local address."""
    if not url or any(ord(char) < 32 or ord(char) == 127 for char in url):
        return False
    return re.sub(r"\s+", "", url).lower().startswith(("http://", "https://", "mailto:", "/", "#"))


def user_links(state):
    """A typed link opens in a new tab if its address is safe, and is left as its text otherwise."""
    for token in state.tokens:
        opened = []
        for child in token.children or []:
            if child.type == "link_open":
                opened.append(child)
                href, title = child.attrs.get("href", ""), child.attrs.get("title")
                child.hidden = not safe_user_url(href)
                child.attrs = {"href": href, "target": "_blank", "rel": "noopener noreferrer nofollow ugc"}
                if title:
                    child.attrs["title"] = title
            elif child.type == "link_close":
                child.hidden = opened.pop().hidden


def escaped_html(renderer, tokens, idx, options, env):
    return escapeHtml(tokens[idx].content)


def image_text(renderer, tokens, idx, options, env):
    return escapeHtml(tokens[idx].content or tokens[idx].attrs.get("title") or "")


def build_user():
    md = build()
    md.core.ruler.push("user_links", user_links)
    md.add_render_rule("html_block", escaped_html)
    md.add_render_rule("html_inline", escaped_html)
    md.add_render_rule("image", image_text)
    md.normalizeLink = lambda url: url
    return md


USER = build_user()


def render_user(text: str) -> str:
    """A person's message as the page shows it: Markdown, its HTML as text, its images as their names."""
    return USER.render(text)
