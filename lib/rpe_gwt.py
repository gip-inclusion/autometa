"""Construction browserless de l'appel getFlowsView à partir des frames du wallet RPE."""

import re
from urllib.parse import unquote

GWT = {
    "getUserSettings": "7|3|13|https://pilotage-rpe.francetravail.org/digdash_dashboard/dashboard/|B28E527AF46D9C6155A876F4769EC2F4|24|2B78659DE92186E80F59DE304F511AFD|_|getUserSettings|s|2y|2z|ddenterpriseapi|https://pilotage-rpe.francetravail.org/digdash_dashboard/|2q|public|1|2|3|4|5|6|1|7|7|8|0|0|0|0|-1|9|0|9|0|8|0|0|10|0|0|11|0|1|0|1|0|0|0|0|8|0|0|0|12|0|8|0|0|-1|0|8|0|0|13|",
    "login": "7|3|43|https://pilotage-rpe.francetravail.org/digdash_dashboard/dashboard/|B28E527AF46D9C6155A876F4769EC2F4|24|2B78659DE92186E80F59DE304F511AFD|_|login|s|2i|2y|2z|ERR-DD-LOG003_URL|ERR-DD-LOG002_MSG|ERR-DD-LOG004_MSG|studio_domain|studio|ERR-DD-LOG008_URL|ERR-DD-LOG009_MSG|ERR-DD-LOG005_URL|ERR-DD-LOG007_MSG|studio_url|ERR-DD-LOG006_URL|adminconsole_domain|adminconsole|cryptPass|ERR-DD-LOG001_URL|ERR-DD-LOG008_MSG|ERR-DD-LOG009_URL|urlLogout|ERR-DD-LOG003_MSG|ERR-DD-LOG002_URL|ERR-DD-LOG007_URL|ERR-DD-LOG006_MSG|ERR-DD-LOG004_URL|ERR-DD-LOG005_MSG|URLLOGINPANEL|ERR-DD-LOG001_MSG|ddenterpriseapi|https://pilotage-rpe.francetravail.org/digdash_dashboard/|en|2q|RPE_V2|public|__RPE_PASS__|1|2|3|4|5|6|2|7|8|7|9|0|0|1|0|-1|10|0|10|0|9|24|8|11|0|8|12|0|8|13|0|8|14|8|15|8|16|0|8|17|0|8|18|0|8|19|0|8|20|0|8|21|0|8|22|8|23|8|24|0|8|25|0|8|26|0|8|27|0|8|28|0|8|29|0|8|30|0|8|31|0|8|32|0|8|33|0|8|34|0|8|35|0|8|36|0|0|37|1|1|38|0|1|0|0|0|0|39|0|9|0|0|0|40|0|9|0|0|-1|0|9|0|41|42|43|",
    "loadWallet": "7|3|15|https://pilotage-rpe.francetravail.org/digdash_dashboard/dashboard/|B28E527AF46D9C6155A876F4769EC2F4|24|6B7CB8DE0BE915D32C64AA4A55FCAEAB|_|loadWallet|s|2y|2z|ddenterpriseapi|https://pilotage-rpe.francetravail.org/digdash_dashboard/|4c9184f37cff01bcdc32dc486ec36961b42616b5412e1a211780667518540|fr|2q|public|1|2|3|4|5|6|1|7|7|8|0|0|0|0|-1|9|0|9|0|8|0|0|10|0|0|11|12|1|0|1|0|0|13|0|8|0|0|0|14|0|8|0|0|-1|0|8|0|0|15|",
    "getUserParams": '7|3|138|https://pilotage-rpe.francetravail.org/digdash_dashboard/dashboard/|B28E527AF46D9C6155A876F4769EC2F4|24|6B7CB8DE0BE915D32C64AA4A55FCAEAB|_|getUserParams|s|31|2i||2q|AccessDBV|AddCommentDataModel|AddCommentFlow|AddFormData|ChartNavigation|DashboardNavigationMenu|DashboardOfflineMode|PrintChart|RemoveCommentDataModel|RemoveCommentFlow|SaveAsCSV|SaveAsPDF|SaveAsPPT|SaveAsXLS|SaveAsXLSWithoutStyles|SaveView|SendSMS|TextQuery|UseAdHocAnalysis|ViewAllComments|ViewComments|b|a|2y|1329815938_help|tooltip|2z|SCALINGSIZE|DEACTIVATECHARTDISPLAYINEDITOR|false|ERR-DD-LOG002_MSG|DEFAULTDISPLAY|grid|MARGINGRID|10|ERR-DD-LOG005_URL|ERR-DD-LOG007_MSG|studio_url|ERR-DD-LOG006_URL|HIDEREFRESHMENU|ERR-DD-LOG001_URL|DISPLAYONLYVISIBLECHARTS|NAVIGATIONMENUPOSITION|left|ERR-DD-LOG002_URL|ERR-DD-LOG007_URL|NAVIGATIONMENUWIDTH|300|ERR-DD-LOG006_MSG|ERR-DD-LOG005_MSG|DASHBOARDTITLE|${currentrole} |theme|RPE_V2|DASHBOARDTITLE_fr|ERR-DD-LOG001_MSG|ADMINMESSAGE|<AdminMessage><title><value locale="default">Message des administrateurs</value></title><message/><show>false</show></AdminMessage>|ERR-DD-LOG003_URL|ERR-DD-LOG004_MSG|NAVIGATIONBREADCRUMB|true|studio_domain|studio|ERR-DD-LOG008_URL|ERR-DD-LOG009_MSG|NAVIGATIONDEFAULTDISPLAY|HIDEFILTERS|DISPLAYTEMPLATE|HIDENAVIGATIONMENU|adminconsole_domain|adminconsole|cryptPass|ERR-DD-LOG008_MSG|ERR-DD-LOG009_URL|DISPLAYLOADINGPAGE|THRESHOLDSMALLSCREEN|450|urlLogout|ERR-DD-LOG003_MSG|NAVIGATIONMODE|VERTICAL|ERR-DD-LOG004_URL|NBLINE|1|URLLOGINPANEL|Public RPE|ddenterpriseapi|https://pilotage-rpe.francetravail.org/digdash_dashboard/|4c9184f37cff01bcdc32dc486ec36961b42616b5412e1a211780667518540|fr|g|f|en|Anglais (en)|Français (fr)|DDAudit|Rapport de fréquentation|search|Recherche|comments|Commentaires|legend|Légende|filters|Eléments filtrés|Focus sur l\'accompagnement rénové des bénéficiaires du RSA|Focus sur l\'accompagnement rénové des bénéficiaires du RSA (territoires pilotes)|Portail_du_réseau_pour_l_emploi_12221ae1|e|Portail du réseau pour l\'emploi|R|New_DDAudit_5f933519|99|ac78d0ed|Tableau de bord du Réseau pour l\'Emploi|2|e4f2b0a6|3|{"id":"Europe/Paris","name":"Central European Standard Time","offset":-60,"dstOffset":-60,"dstInfo":{"ts":[0,196819200,212540400,228877200,243997200,260326800,276051600,291776400,307501200,323830800,338950800,354675600,370400400,386125200,401850000,417574800,433299600,449024400,465354000,481078800,496803600,512528400,528253200,543978000,559702800,575427600,591152400,606877200,622602000,638326800,654656400,670381200,686106000,701830800,717555600,733280400,749005200,764730000,780454800,796179600,811904400,828234000,846378000,859683600,877827600,891133200,909277200,922582800,941331600,954032400,972781200,985482000,1004230800,1017536400,1035680400,1048986000,1067130000,1080435600,1099184400,1111885200,1130634000,1143334800,1162083600,1174784400,1193533200,1206838800,1224982800,1238288400,1256432400,1269738000,1288486800,1301187600,1319936400,1332637200,1351386000,1364691600,1382835600,1396141200,1414285200,1427590800,1445734800,1459040400,1477789200,1490490000,1509238800,1521939600,1540688400,1553994000,1572138000,1585443600,1603587600,1616893200,1635642000,1648342800,1667091600,1679792400,1698541200,1711846800,1729990800,1743296400,1761440400],"dst":[0,1,0,1,0,1,0,1,0,1,0,1,0,1,0,1,0,1,0,1,0,1,0,1,0,1,0,1,0,1,0,1,0,1,0,1,0,1,0,1,0,1,0,1,0,1,0,1,0,1,0,1,0,1,0,1,0,1,0,1,0,1,0,1,0,1,0,1,0,1,0,1,0,1,0,1,0,1,0,1,0,1,0,1,0,1,0,1,0,1,0,1,0,1,0,1,0,1,0,1,0],"startM":69},"tester":{"1767222000":0,"1782856800":0}}|digdashMail|Adresse Email|uid|Identifiant de connexion LDAP|displayName|Nom affiché|public|1|2|3|4|5|6|1|7|7|8|0|1|9|10|11|21|9|12|9|13|9|14|9|15|9|16|9|17|9|18|9|19|9|20|9|21|9|22|9|23|9|24|9|25|9|26|9|27|9|28|9|29|9|30|9|31|9|32|0|1|33|1|34|0|35|0|1|0|0|0|0|36|1|0|0|0|35|0|0|0|0|35|0|0|37|0|-1|38|0|38|0|35|45|9|39|-4|9|40|9|41|9|42|0|9|43|9|44|9|45|9|46|9|47|0|9|48|0|9|49|0|9|50|0|9|51|-37|9|52|0|9|53|-37|9|54|9|55|9|56|0|9|57|0|9|58|9|59|9|60|0|9|61|0|9|62|9|63|9|64|9|65|9|66|-4|9|67|0|9|68|9|69|9|70|0|9|71|0|9|72|9|73|9|74|9|75|9|76|0|9|77|0|9|78|-4|9|79|-69|9|80|-4|9|81|-37|9|82|9|83|9|84|0|9|85|0|9|86|0|9|87|-37|9|88|9|89|9|90|0|9|91|0|9|92|9|93|9|94|0|9|95|9|96|9|97|0|98|99|1|1|100|101|0|1|0|0|1|102|103|2|104|105|105|106|104|102|102|107|35|6|9|108|9|109|9|110|9|111|9|112|9|113|9|114|9|115|9|116|9|117|9|118|9|119|0|0|11|0|35|4|9|120|121|120|122|96|123|9|124|121|124|108|125|123|9|126|121|126|127|128|123|9|129|121|129|118|130|123|0|-1|131|35|3|9|132|9|133|9|134|9|135|9|136|9|137|65|138|',
    "getFlowsView": "7|3|19|https://pilotage-rpe.francetravail.org/digdash_dashboard/dashboard/|B28E527AF46D9C6155A876F4769EC2F4|24|6B7CB8DE0BE915D32C64AA4A55FCAEAB|_|getFlowsView|s|2j|I|Z|2i|2y|2z|ddenterpriseapi|https://pilotage-rpe.francetravail.org/digdash_dashboard/|4c9184f37cff01bcdc32dc486ec36961b42616b5412e1a211780667518540|fr|2q|public|1|2|3|4|5|6|5|7|8|9|10|11|7|12|0|0|0|0|-1|13|0|13|0|12|0|0|14|0|0|15|16|1|0|1|0|0|17|0|12|0|0|0|18|0|12|0|0|-1|0|12|0|0|19|8|0|0|1|0|",
}

SEL = {
    "axis": [None, [0]],
    "complexGroup": False,
    "measureAxis": 0,
    "dimsToExplore": [
        {"dim": "C_PARCOURSENTREE", "enabled": True, "hPos": -1, "lPos": -1, "format": None, "displayMode": 0}
    ],
    "dimsToFilter": [],
    "measuresToKeep": ["Taux de parcours en entrée"],
    "targetsForMeasure": [None],
    "aggsForMeasure": [-1],
    "fmtsForMeasure": [None],
    "valueFilters": [],
    "valueSorters": [],
    "axisSort": [{"axisId": 1, "type": 0, "reverse": False, "measure": -1, "measureName": None, "onCaption": False}],
    "sortOrder": [{"axisId": 1, "type": 0, "reverse": False, "measure": -1, "measureName": None, "onCaption": False}],
    "ddVars": [
        {"name": "TypeCumul", "cur": 0, "def": 0, "min": 0, "max": 0, "inc": 0},
        {"name": "Vision d'orientation", "cur": 1, "def": 1, "min": 0, "max": 0, "inc": 0},
        {"name": "NiveauAxeTemps", "cur": 0, "def": 0, "min": 0, "max": 0, "inc": 0},
        {"name": "Vision d'accompagnement_orientation", "cur": 0, "def": 0, "min": 0, "max": 0, "inc": 0},
        {"name": "Vision d'accompagnement_freins", "cur": 0, "def": 0, "min": 0, "max": 0, "inc": 0},
        {"name": "Vision d'accompagnement", "cur": 0, "def": 0, "min": 0, "max": 0, "inc": 0},
        {"name": "Vision d'accompagnement_orientation_msa", "cur": 0, "def": 0, "min": 0, "max": 0, "inc": 0},
    ],
    "pivot": 0,
    "overallAxis": [],
    "axisMemberSeparators": [None, "-"],
    "retainNull": False,
    "crossOveralls": False,
    "fullMeasureSort": -1,
    "fullMeasureSortReverse": False,
    "fullMeasureSortPreserveTotal": False,
    "measuresToKeepHidden": [False],
    "measuresToKeepHiddenLabel": [False],
    "realLineCount": None,
    "imageKey": None,
    "forceAxisList": [],
    "forceCrossAxisList": [],
    "filterRules": [],
    "chartMeasures": [],
    "fullMeasureFilter": -1,
    "fullMeasureFilterType": -1,
    "fullMeasureFilterTopBottomValue": 1,
    "fullMeasureFilterTopBottomShowOthers": False,
    "fullMeasureFilterRangeMinValue": "",
    "fullMeasureFilterRangeMaxValue": "",
    "dimsToDisplayFilter": [],
    "dimSets": [],
    "dimensionsToExcludeForNavigation": ["C_AUROREAGENCE_COMP_ID"],
    "drillPaths": [],
    "axisGPos": [],
    "measuresGPos": [],
}

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
_JS_ESC_RE = re.compile(r"\\x([0-9a-fA-F]{2})|\\u([0-9a-fA-F]{4})|\\(.)")
# Why: dans le flux GWT, "\n" est la séquence littérale (backslash+n), pas un vrai saut de ligne.
_ITEM_SPLIT_RE = re.compile(r"\\n\s*-\s*")


def _js_str(s: str) -> str:
    """Décode les échappements de chaîne JS/GWT (\\xNN, \\uXXXX, \\') d'un littéral capturé."""
    return _JS_ESC_RE.sub(
        lambda m: chr(int(m.group(1) or m.group(2), 16)) if (m.group(1) or m.group(2)) else m.group(3), s
    )


def _clean(s: str) -> str:
    """Libellé de graphe : retours ligne GWT supprimés puis échappements décodés."""
    return _js_str(s.replace("\\n", " ")).strip()


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


_CUBEURL_RE = re.compile(r"cubeURL\\u003D(.*?)\\u0026")
_CUBE_DM_KEY_RE = re.compile(r"cube_dm_([0-9a-f]{32})_[0-9a-f]{32}_")
_CUBENAME_RE = re.compile(r"dm\.cubeName='((?:[^'\\]|\\.)*)'")
# Why: addDim a deux formes — addDim(pos,id,name) et addDim(pos,id,name,0) — d'où le [,)] terminal.
_ADDDIM_RE = re.compile(r"dm\.addDim\(\d+,'((?:[^'\\]|\\.)*)','((?:[^'\\]|\\.)*)'[,)]")


def cube_dm_urls(flows_response: str) -> dict[str, str]:
    """Mappe cube_key → URL getFile du fichier cube_dm (catalogue), extraite des URLs genDocView du getFlowsView."""
    urls: dict[str, str] = {}
    for encoded in _CUBEURL_RE.findall(flows_response):
        url = unquote(encoded)
        m = _CUBE_DM_KEY_RE.search(url)
        if m:
            urls[m.group(1)] = url
    return urls


def _dim_attr(block: str, attr: str) -> str | None:
    m = re.search(r"dim\.%s='((?:[^'\\]|\\.)*)'" % attr, block)
    return _js_str(m.group(1)) if m else None


def parse_cube_dm(js: str) -> dict:
    """Cube depuis son cube_dm : cubeName + dimensions (les mesures y sont des intermédiaires techniques, pas les requêtables — cf. graphes)."""
    name = _CUBENAME_RE.search(js)
    dim_matches = list(_ADDDIM_RE.finditer(js))
    dims = []
    for i, m in enumerate(dim_matches):
        if i + 1 < len(dim_matches):
            end = dim_matches[i + 1].start()
        else:  # dernière dim : borne à la 1re mesure qui la suit (les mesures suivent les dims)
            nxt = js.find("dm.addMeasure", m.end())
            end = nxt if nxt != -1 else len(js)
        block = js[m.end() : end]
        members = re.search(r"dim\.nbMembers=(\d+)", block)
        time = re.search(r"dim\.time=(true|false)", block)
        dims.append({
            "id": m.group(1),
            "name": _js_str(m.group(2)),
            "category": _dim_attr(block, "category"),
            "caption_dim": _dim_attr(block, "captionDim"),
            "n_members": int(members.group(1)) if members else None,
            "time": time.group(1) == "true" if time else None,
        })
    return {"cube_name": _js_str(name.group(1)) if name else None, "dimensions": dims}
