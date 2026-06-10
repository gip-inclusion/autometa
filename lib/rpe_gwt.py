"""Construction browserless de l'appel getFlowsView à partir des frames du wallet RPE."""

import re

_QUOTED_RE = re.compile(r'"([^"]*)"')
_WIDGET_ID_RE = re.compile(r"[0-9a-f]{6,8}")
# Préfixe du flux d'entiers GWT de getFlowsView, jusqu'au marqueur de liste d'items (« 19|8 »).
_FLOWSVIEW_INT_PREFIX = (
    "1|2|3|4|5|6|5|7|8|9|10|11|7|12|0|0|0|0|-1|13|0|13|0|12|0|0|14|0|0|15|16|1|0|1|0|0"
    "|17|0|12|0|0|0|18|0|12|0|0|-1|0|12|0|0|19|8"
)


def extract_frame_ids(wallet_text: str) -> list[str]:
    """Identifiants courts (hex 6-8) des frames/widgets dans la table de chaînes du wallet, dédupliqués."""
    return [s for s in dict.fromkeys(_QUOTED_RE.findall(wallet_text)) if _WIDGET_ID_RE.fullmatch(s)]


def flowsview_header(flowsview_payload: str) -> list[str]:
    """Les 19 chaînes d'en-tête fixes d'un payload getFlowsView capturé (URL, strong-name, sid, locale…)."""
    return flowsview_payload.split("|")[3:22]


def build_flowsview_payload(frame_ids: list[str], header_strings: list[str]) -> str:
    """Payload GWT getFlowsView demandant les flux de tous les frames donnés (tous les cubeIds en un appel)."""
    items = ["ItemIdentifier(public\\!%s\\!-1)" % fid for fid in frame_ids]
    strings = list(header_strings) + items
    n = len(items)
    refs = "|".join(str(20 + i) for i in range(n))
    ints = _FLOWSVIEW_INT_PREFIX + "|" + str(n) + (("|" + refs) if refs else "") + "|0|1|0|"
    return "7|3|%d|%s|%s" % (len(strings), "|".join(strings), ints)


_CHART_RE = re.compile(r"^(.*) report([0-9a-f]{32})$")
_UNICODE_ESC_RE = re.compile(r"\\u([0-9a-fA-F]{4})")
# Why: dans le flux GWT, "\n" est la séquence littérale (backslash+n), pas un vrai saut de ligne.
_ITEM_SPLIT_RE = re.compile(r"\\n\s*-\s*")


def _clean(s: str) -> str:
    """Décode les échappements GWT (\\uXXXX) et supprime les retours ligne d'un libellé."""
    s = s.replace("\\n", " ")
    s = _UNICODE_ESC_RE.sub(lambda m: chr(int(m.group(1), 16)), s)
    return s.strip()


def parse_charts(flows_response: str) -> list[dict]:
    """Décrit chaque graphe (titre, cube_key, mesures/dimensions affichées) depuis une réponse getFlowsView."""
    strings = re.findall(r'"((?:[^"\\]|\\.)*)"', flows_response)
    out: list[dict] = []
    seen: set[tuple] = set()
    for i, s in enumerate(strings):
        if i == 0 or not s.startswith("Measures"):
            continue
        m = _CHART_RE.match(strings[i - 1])
        if not m:
            continue
        title, cube_key = _clean(m.group(1)), m.group(2)
        meas_part, _, dim_part = s.partition("Dimensions")
        measures = [c for c in (_clean(x) for x in _ITEM_SPLIT_RE.split(meas_part)[1:]) if c]
        dims = [c for c in (_clean(x) for x in _ITEM_SPLIT_RE.split(dim_part)) if c]
        key = (title, cube_key, tuple(measures), tuple(dims))
        if key in seen:
            continue
        seen.add(key)
        out.append({"chart_title": title, "cube_key": cube_key, "measures_shown": measures, "dims_shown": dims})
    return out
