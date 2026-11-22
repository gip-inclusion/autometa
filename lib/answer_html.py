"""Conversation Markdown as HTML: markdown-it-py tuned to marked 15.0.12, then nh3 with the page's DOMPurify policy."""

import bisect
import html
import logging
import re
import secrets
from collections import Counter, defaultdict
from dataclasses import dataclass
from functools import partial
from urllib.parse import quote

import nh3
from markdown_it import MarkdownIt
from markdown_it.common.utils import escapeHtml, isMdAsciiPunct, isPunctChar, isWhiteSpace
from markdown_it.renderer import RendererHTML
from markdown_it.rules_inline.state_inline import Delimiter, Scanned
from markdown_it.token import Token

__all__ = ["Link", "render_answer", "render_user"]

# Why: markdown-it logs each rule it tries, thousands of lines per conversation; where the application logs at debug
# level, writing them took four times as long as rendering.
logging.getLogger("markdown_it").setLevel(logging.WARNING)

# marked 15 GFM extended autolinks (inline.url): this head, then all that comes before a space or a <.
URL_HEAD = re.compile(r"((?:ftp|https?)://|www\.)(?:[a-zA-Z0-9\-]+\.?)+", re.I)
URL_STOP = re.compile(r"[\s<]")
# marked leaves these as entities in text, so the browser decodes them, inside a bare URL too.
ENTITY = re.compile(r"&(?:#\d{1,7}|#[Xx][a-fA-F0-9]{1,6}|\w+);")
EMAIL_DOMAIN = re.compile(r"@[a-zA-Z0-9-_]+(?:\.[a-zA-Z0-9-_]*[a-zA-Z0-9])+(?![-_])")
# markdown-it's text terminators, plus where marked's text rule stops for an autolink to start.
TEXT_STOP = re.compile(
    r"[\n!#$%&*+\-:<=>@\[\\\]^_`{}~]|(?:https?|ftp)://|www\.|(?<![A-Za-z0-9._+-])[A-Za-z0-9._+-]+"
    + EMAIL_DOMAIN.pattern
)


def marked_href(url):
    """marked's cleanUrl: encodeURI, then %25 back to %."""
    return quote(url, safe=";,/?:@&=+$-_.!~*'()#").replace("%25", "%")


def marked_text(state, silent):
    # Why: marked tries a URL before text where a token starts, its pattern ignoring case; its text stops do not.
    if URL_HEAD.match(state.src, state.pos, state.posMax):
        return False
    stop = TEXT_STOP.search(state.src, state.pos, state.posMax)
    end = stop.start() if stop else state.posMax
    if end == state.pos:
        return False
    if not silent:
        state.pending += state.src[state.pos : end]
    state.pos = end
    return True


def ahead(state, key, pos, find):
    """find(pos): the first place of something from pos on, state.posMax when there is none, sought once per stretch."""
    if getattr(state, "ahead_src", None) is not state.src:
        state.ahead_src, state.ahead = state.src, {}
    asked, found = state.ahead.get((key, state.posMax), (1, 0))
    # Why: the answer for an earlier place holds until it is passed; asked from each place, a long text is read each time.
    if not asked <= pos <= found:
        found = find(pos)
        state.ahead[key, state.posMax] = (pos, found)
    return found


def first(state, char, pos):
    """The first `char` of the text from pos on, state.posMax when there is none."""
    at = state.src.find(char, pos, state.posMax)
    return state.posMax if at == -1 else at


def url_stop(state, pos):
    stop = URL_STOP.search(state.src, pos, state.posMax)
    return stop.start() if stop else state.posMax


def ascii_alnum(char):
    return char.isascii() and char.isalnum()


def url_end(state, start):
    """Where the bare URL that starts at `start` ends: marked's _backpedal applied until nothing changes, in one pass."""
    src = state.src
    stop = ahead(state, "url stop", start, partial(url_stop, state))
    # Why: an & that opens an entity running to the end of the text read stops the URL; where that entity's name
    # starts is the same for every URL of the stretch.
    if ("name", stop) not in state.ahead:
        name = stop - 1
        while src[stop - 1] == ";" and name and ascii_alnum(src[name - 1]):
            name -= 1
        state.ahead["name", stop] = name
    name = state.ahead["name", stop]
    end, closers = start, set()
    while end < stop:
        char = src[end]
        if char == "(":
            close = ahead(state, ")", end, partial(first, state, ")"))
            # Why: a parenthesis never closed ends the URL before it.
            if close >= stop:
                break
            closers.add(close)
            end = close + 1
        elif char == "&" and name <= end + 1 < stop - 1:
            break
        elif char in "?!.,:;*_'\"~)":
            run = end
            while run < stop and src[run] in "?!.,:;*_'\"~)":
                run += 1
            # Why: punctuation that runs to the end of the text read gives up its last mark, and the URL stops there.
            if run == stop:
                end = run - 1
                break
            end = run
        else:
            end += 1
    # Why: from then on, each pass of marked drops one closing mark or one whole entity from the end; a closing
    # parenthesis stays when it closes one opened in the URL.
    while end > start:
        entity = end - 1
        if src[entity] == ";":
            while entity > start and ascii_alnum(src[entity - 1]):
                entity -= 1
            if start < entity < end - 1 and src[entity - 1] == "&":
                end = entity - 1
                continue
        if src[end - 1] not in "?!.,:;*_'\"~)" or end - 1 in closers:
            break
        end -= 1
    return end


def email_at(state):
    """marked's bare email at state.pos; each @ of the text is looked for and read once, wherever it is tried from."""
    src, pos, end = state.src, state.pos, state.posMax
    at = ahead(state, "@", pos, partial(first, state, "@"))
    if at == pos or at == end:
        return None
    if ("email", at, end) not in state.ahead:
        start = at
        while start and (ascii_alnum(src[start - 1]) or src[start - 1] in "._+-"):
            start -= 1
        domain = EMAIL_DOMAIN.match(src, at, end)
        state.ahead["email", at, end] = (start, domain.end() if domain else 0)
    start, stop = state.ahead["email", at, end]
    return src[pos:stop] if start <= pos and stop else None


def marked_url(state, silent):
    # Why: silent is a link label being scanned; marked matches the whole link first, so nothing inside spills past ].
    if silent or state.linkLevel > 0:
        return False
    email = email_at(state)
    if email:
        text, href = email, "mailto:" + email
    else:
        m = URL_HEAD.match(state.src, state.pos, state.posMax)
        if not m:
            return False
        text = state.src[state.pos : url_end(state, state.pos)]
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


def next_closer(state, char, pos):
    """The first run of `char` from pos on that may close an emphasis, state.posMax when there is none."""
    i = state.src.find(char, pos, state.posMax)
    while i != -1 and not marked_scan(state, i, char == "*").can_close:
        while i < state.posMax and state.src[i] == char:
            i += 1
        i = state.src.find(char, i, state.posMax)
    return state.posMax if i == -1 else i


def emphasis_limit(state):
    """Where an emphasis opened before this point closes: marked reads a tilde only inside it."""
    if getattr(state, "emphasis_src", None) is not state.src:
        state.emphasis_src, state.emphasis = state.src, {}
    # Why: the delimiters of a level only grow, and a level comes back once a nested one closes; those read for an
    # earlier tilde are not read again. The list is kept so that no other takes its identity.
    level = state.emphasis.setdefault(id(state.delimiters), [state.delimiters, 0, [], Counter()])
    _, read, pending, opened = level
    for d in state.delimiters[read:]:
        if d.marker not in (0x2A, 0x5F):
            continue
        if d.close and opened[d.marker]:
            while (marker := pending.pop()) != d.marker:
                opened[marker] -= 1
            opened[d.marker] -= 1
        elif d.open:
            pending.append(d.marker)
            opened[d.marker] += 1
    level[1] = len(state.delimiters)
    closers = (chr(marker) for marker, count in opened.items() if count)
    return min([state.posMax, *(ahead(state, char, state.pos, partial(next_closer, state, char)) for char in closers)])


def backslashes_before(src, i):
    start = i
    while start and src[start - 1] == "\\":
        start -= 1
    return i - start


def tilde_closers(src):
    """Tilde runs marked's strikethrough may close on: {start: length}, after a char that may end its text."""
    found = {}
    for run in re.finditer(r"~+", src):
        j, size = run.start(), len(run[0])
        slashes = backslashes_before(src, j)
        if slashes % 2:
            j, size, last_ok = j + 1, size - 1, True
        elif slashes or j == 0:
            last_ok = slashes > 0
        else:
            last_ok = bool(backslashes_before(src, j - 1) % 2) or not src[j - 1].isspace()
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


TILDES = re.compile(r"[`~]+")


def marked_strikethrough(state, silent):
    if silent or state.src[state.pos] != "~":
        return False
    m = del_match(state, emphasis_limit(state))
    if not m:
        # Why: marked's text rule takes a run of tildes and backticks whole, so a backtick after ~ opens no code.
        run = TILDES.match(state.src, state.pos, state.posMax)[0]
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


def join_text(state):
    """markdown-it's fragments_join: adjacent text tokens become the last of them, each run joined once."""
    kept, run, level = [], [], 0
    for token in state.tokens:
        if token.nesting < 0:
            level -= 1
        token.level = level
        if token.nesting > 0:
            level += 1
        if token.type == "text":
            run.append(token)
            continue
        if run:
            run[-1].content = "".join(text.content for text in run)
            kept.append(run[-1])
            run = []
        kept.append(token)
    if run:
        run[-1].content = "".join(text.content for text in run)
        kept.append(run[-1])
    state.tokens[:] = kept


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
    """A list item whose source opens with [ ] or [x] gets a checkbox token in place of it, as in a GFM task list."""
    tokens = state.tokens
    for i in range(2, len(tokens)):
        item = tokens[i]
        if (
            item.type == "inline"
            and tokens[i - 1].type == "paragraph_open"
            and tokens[i - 2].type == "list_item_open"
            and item.content.startswith(("[ ] ", "[x] ", "[X] "))
        ):
            box, kids = Token("task_checkbox", "", 0, meta={"checked": item.content[1] != " "}), item.children
            # Why: where the text defines a reference named x, the box was read as a link to it.
            if kids[0].type == "link_open":
                del kids[: next(n for n, kid in enumerate(kids) if kid.type == "link_close") + 1]
            else:
                kids[0].content = kids[0].content[3:]
            kids.insert(0, box)


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
    md.inline.ruler.at("text", marked_text)
    md.inline.ruler.at("emphasis", marked_emphasis)
    md.inline.ruler.before("emphasis", "marked_strikethrough", marked_strikethrough)
    md.inline.ruler.before("autolink", "marked_url", marked_url)
    # Why: markdown-it joins text tokens pair by pair, copying the text so far each time; a long run of marks is quadratic.
    md.inline.ruler2.at("fragments_join", join_text)
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


# DOMPurify's URI_SAFE_ATTRIBUTES, ATTR_WHITESPACE and IS_ALLOWED_URI: what it reads of a value before keeping it.
URI_SAFE_ATTRS = set("alt class for id label name pattern placeholder role summary title value style xmlns".split())
ATTR_WHITESPACE = re.compile("[\u0000-\u0020\u00a0\u1680\u180e\u2000-\u2029\u205f\u3000]")
ALLOWED_URI = re.compile(
    r"(?:(?:(?:f|ht)tps?|mailto|tel|callto|sms|cid|xmpp|matrix):|[^a-z]|[a-z+.\-]+(?:[^a-z+.\-:]|\Z))", re.I
)


def keep_attribute(mark, element, attribute, value):
    """Only code keeps a class, only a language- one; any other value is judged as DOMPurify judges an address."""
    if attribute == "class":
        language = element == "code" and re.fullmatch(r"language-[\w-]+", value)
        return value if language or value.startswith(mark) else None
    # Why: a browser skips spaces and control characters when it reads a scheme, wherever the attribute is.
    if attribute in URI_SAFE_ATTRS or not value or ALLOWED_URI.match(ATTR_WHITESPACE.sub("", value)):
        return value
    media = attribute == "src" and element in ("img", "audio", "video", "source", "track")
    return value if media and value.startswith("data:") else None


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


# Why: compiled once; a pattern holding the mark of each render would be compiled at each.
MARKED = re.compile(r'(<span )?class="(m[0-9a-f]{32})([bcef])(\d*)"(?(1)></span>)')


def render_answer(text: str, links: tuple[Link, ...] = ()) -> str:
    """Agent text as the page shows it, sanitized; each link written on its element with its button."""
    # Why: what the app adds goes through the sanitizer under a class no answer can guess, then takes its real form.
    mark = f"m{secrets.token_hex(16)}"
    tokens = place_links(ANSWER.parse(text), links, mark)
    cleaned = clean(ANSWER.renderer.render(tokens, ANSWER.options, {"mark": mark}), mark)

    def written(m):
        if m[2] != mark:
            return m[0]
        kind, n = m[3], int(m[4] or 0)
        if kind == "b":
            return links[n].button
        if kind == "c":
            return CHECKBOX[n]
        return links[n].attributes if kind == "e" else 'class="permalink-figure"'

    return MARKED.sub(written, cleaned)


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
