"""Client du tableau de bord RPE (France Travail / DigDash) : login, requêtes à la demande, catalogue. httpx pur."""

import json
import logging
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import httpx
from sqlalchemy import Column, DateTime, Float, Integer, MetaData, String, Table, delete, insert, select, text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.exc import SQLAlchemyError

from web.alerts import notify_alert_channel
from web.db import get_engine

logger = logging.getLogger(__name__)

# Données publiques du tableau de bord en accès libre (identifiants présents dans l'URL publique).
BASE = "https://pilotage-rpe.francetravail.org/digdash_dashboard"
MODULE = BASE + "/dashboard/"
PUBLIC_PASS = "yYjL2p#9LSHeT8p0"
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0 Safari/537.36"
REFERER = BASE + "/index.html?domain=ddenterpriseapi&user=public&pass=yYjL2p%239LSHeT8p0"
TIMEOUT = 60
SCHEMA = "matometa"
SESSION_TTL_S = 1200  # < 30 min Tomcat idle ; un 403 déclenche de toute façon un re-login

# Valeurs liées au build GWT, re-scrapables en cas d'échec de login (cf. _scrape_builds).
BAKED_PERMUTATION = "2D1551B7C160B162D34A4CD10515557B"
BAKED_STRONG_NAME = "B28E527AF46D9C6155A876F4769EC2F4"

_RES = json.loads((Path(__file__).parent / "rpe_templates.json").read_text(encoding="utf-8"))
_SID_RE = re.compile(r"4c9184f37cff01[0-9a-f]+")
_CUBE_RE = re.compile(r"[0-9a-f]{32}_[0-9a-f]{32}_[0-9a-f]+_[0-9]{13}")
_HEX32_RE = re.compile(r"[0-9A-F]{32}")


class RpeLoginError(RuntimeError):
    """Login RPE impossible (identifiants ou valeurs de build GWT obsolètes)."""


_metadata = MetaData(schema=SCHEMA)
rpe_theme = Table("rpe_theme", _metadata, Column("role_id", String, primary_key=True), Column("name", String))
rpe_dataset = Table(
    "rpe_dataset",
    _metadata,
    Column("cube_key", String, primary_key=True),
    Column("name", String),
    Column("cube_id", String),
    Column("role_id", String),
)
rpe_dimension = Table(
    "rpe_dimension",
    _metadata,
    Column("dataset", String, primary_key=True),
    Column("dim_id", String, primary_key=True),
    Column("name", String),
    Column("category", String),
    Column("caption_dim", String),
    Column("n_members", Integer),
)
rpe_measure = Table(
    "rpe_measure",
    _metadata,
    Column("dataset", String, primary_key=True),
    Column("measure_id", String, primary_key=True),
    Column("label", String),
)
rpe_fact = Table(
    "rpe_fact",
    _metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("dataset", String),
    Column("measure", String),
    Column("measure_id", String),
    Column("period", String),
    Column("dimension", String),
    Column("member_code", String),
    Column("member_label", String),
    Column("value", Float),
)
rpe_session = Table(
    "rpe_session",
    _metadata,
    Column("id", Integer, primary_key=True),
    Column("jsessionid", String),
    Column("sid", String),
    Column("created_at", DateTime(timezone=True)),
)


def ensure_schema() -> None:
    eng = get_engine()
    with eng.begin() as conn:
        conn.execute(text("CREATE SCHEMA IF NOT EXISTS " + SCHEMA))
    _metadata.create_all(eng)


def load_cached_session() -> Optional[tuple[str, str]]:
    """Renvoie (jsessionid, sid) en cache si frais (< SESSION_TTL_S), sinon None."""
    try:
        eng = get_engine()
        with eng.connect() as conn:
            if not eng.dialect.has_table(conn, "rpe_session", schema=SCHEMA):
                return None
            row = conn.execute(select(rpe_session).order_by(rpe_session.c.created_at.desc()).limit(1)).first()
    except SQLAlchemyError as e:
        logger.warning("RPE : lecture session en cache impossible (%s)", e)
        return None
    if not row or not row.jsessionid:
        return None
    age = (datetime.now(timezone.utc) - row.created_at).total_seconds()
    if age > SESSION_TTL_S:
        return None
    return row.jsessionid, row.sid


def save_session(jsessionid: Optional[str], sid: Optional[str]) -> None:
    if not jsessionid:
        return
    try:
        with get_engine().begin() as conn:
            conn.execute(delete(rpe_session))
            conn.execute(
                insert(rpe_session),
                [{"id": 1, "jsessionid": jsessionid, "sid": sid, "created_at": datetime.now(timezone.utc)}],
            )
    except SQLAlchemyError as e:  # cache best-effort : le login reste valide sans persistance
        logger.warning("RPE : mise en cache de la session impossible (%s)", e)


def _gwt_headers(permutation: str) -> dict:
    return {
        "User-Agent": UA,
        "Content-Type": "text/x-gwt-rpc; charset=utf-8",
        "X-GWT-Permutation": permutation,
        "X-GWT-Module-Base": MODULE,
        "X-Requested-With": "XMLHttpRequest",
        "Referer": REFERER,
    }


def _ok(resp: httpx.Response) -> bool:
    return resp.status_code == 200 and resp.text.startswith("//OK")


def _attempt_login(permutation: str, strong_name: str) -> Optional[httpx.Client]:
    client = httpx.Client(headers={"User-Agent": UA}, timeout=TIMEOUT)
    headers = _gwt_headers(permutation)

    def gwt(payload: str) -> httpx.Response:
        body = payload.replace(BAKED_STRONG_NAME, strong_name).replace("__RPE_PASS__", PUBLIC_PASS)
        return client.post(MODULE + "dash", content=body, headers=headers, timeout=TIMEOUT)

    settings = gwt(_RES["gwt"]["getUserSettings"])
    login = gwt(_RES["gwt"]["login"])
    if _ok(settings) and _ok(login):
        return client
    client.close()
    return None


def _scrape_builds() -> list[tuple[str, str]]:
    pairs: list[tuple[str, str]] = []
    with httpx.Client(headers={"User-Agent": UA}, timeout=TIMEOUT) as c:
        index = c.get(BASE + "/index.html", timeout=TIMEOUT).text
        m = re.search(r"dashboard/(dashboard\.nocache-[0-9]+\.js)", index)
        if not m:
            return pairs
        nocache = c.get(f"{BASE}/dashboard/{m.group(1)}", timeout=TIMEOUT).text
        for perm in dict.fromkeys(_HEX32_RE.findall(nocache)):
            cache = c.get(f"{BASE}/dashboard/{perm}.cache.js", timeout=TIMEOUT)
            if cache.status_code != 200:
                continue
            for strong in dict.fromkeys(_HEX32_RE.findall(cache.text)):
                if strong != perm:
                    pairs.append((perm, strong))
    return pairs


def login() -> httpx.Client:
    """Ouvre une session authentifiée (httpx) ; re-scrape les valeurs de build et réessaie en cas d'échec."""
    client = _attempt_login(BAKED_PERMUTATION, BAKED_STRONG_NAME)
    if client is not None:
        return client
    logger.warning("RPE login échoué avec les valeurs de build par défaut, re-scraping en cours")
    for permutation, strong_name in _scrape_builds():
        client = _attempt_login(permutation, strong_name)
        if client is not None:
            logger.info("RPE login réussi via build re-scrapé permutation=%s", permutation)
            return client
    raise RpeLoginError("login impossible — identifiants ou valeurs de build GWT (strong-name/permutation) obsolètes")


def _period_of(sel: dict, breakdown_dim: str, member: dict) -> Optional[str]:
    if breakdown_dim and "ate" in breakdown_dim:  # "Date d'observation", "Mois d'entrée…"
        return member.get("f")
    for f in sel.get("dimsToFilter") or []:
        if str(f.get("dim", "")).startswith("D_DATE") and f.get("selectedMembers"):
            secs = int(f["selectedMembers"][0]) + 43200  # bornes de mois en Europe/Paris
            return _epoch_month(secs)
    return None


def _epoch_month(secs: int) -> str:
    return datetime.fromtimestamp(secs, tz=timezone.utc).strftime("%Y-%m")


def _norm(s: str) -> str:
    """Normalise pour le matching de mesure : minuscules, apostrophes unifiées, espaces compactés."""
    return " ".join((s or "").lower().replace("’", "'").replace("‘", "'").replace("´", "'").split())


class RpeClient:
    """Session RPE authentifiée : requêtes getCubeResult arbitraires + rafraîchissement catalogue."""

    def __init__(self, http: httpx.Client, sid: Optional[str] = None):
        self.http = http
        self.sid = sid or self._resolve_sid()
        self.cubeids = self._load_cubeids()

    @classmethod
    def connect(cls) -> "RpeClient":
        """Réutilise la session en cache si fraîche, sinon login httpx (un 403 ultérieur relance un login)."""
        cached = load_cached_session()
        if cached:
            jsessionid, sid = cached
            http = httpx.Client(
                headers={"User-Agent": UA},
                cookies={"JSESSIONID": jsessionid, "digdashSessionId": sid or ""},
                timeout=TIMEOUT,
            )
            return cls(http, sid=sid)
        http = login()
        inst = cls(http)
        save_session(http.cookies.get("JSESSIONID"), inst.sid)
        return inst

    def _relogin(self) -> None:
        self.http.close()
        self.http = login()
        self.sid = self._resolve_sid()
        save_session(self.http.cookies.get("JSESSIONID"), self.sid)

    def close(self) -> None:
        self.http.close()

    def _resolve_sid(self) -> Optional[str]:
        sid = self.http.cookies.get("digdashSessionId")
        if sid:
            return sid
        r = self.http.post(
            MODULE + "dash",
            content=_RES["gwt"]["getUserSettings"].replace("__RPE_PASS__", PUBLIC_PASS),
            headers=_gwt_headers(BAKED_PERMUTATION),
            timeout=TIMEOUT,
        )
        m = _SID_RE.search(r.text)
        return m.group(0) if m else None

    def _load_cubeids(self) -> dict:
        cubeids = {}
        try:
            eng = get_engine()
            with eng.connect() as conn:
                if eng.dialect.has_table(conn, "rpe_dataset", schema=SCHEMA):
                    for row in conn.execute(select(rpe_dataset.c.cube_key, rpe_dataset.c.cube_id)):
                        if row.cube_id:
                            cubeids[row.cube_key] = row.cube_id
        except SQLAlchemyError as e:
            logger.warning("RPE : cubeIds DB indisponibles, repli sur la graine (%s)", e)
        for key, cat in _RES["catalog"].items():  # graine : cubeIds capturés, à défaut de DB
            cubeids.setdefault(key, cat.get("cubeId"))
        return cubeids

    def _key(self, dataset: str) -> str:
        if dataset in _RES["datasets"]:
            return dataset
        for key, d in _RES["datasets"].items():
            if d.get("cubeName") == dataset:
                return key
        raise KeyError(f"dataset inconnu : {dataset}")

    def datasets(self) -> list[str]:
        return [d["cubeName"] for d in _RES["datasets"].values()]

    def measures(self, dataset: str) -> list[dict]:
        return _RES["catalog"][self._key(dataset)]["measures"]

    def dimensions(self, dataset: str) -> list[dict]:
        return _RES["catalog"][self._key(dataset)]["dimensions"]

    def _resolve_measures(self, dataset: str, measures: list) -> list:
        """Résout chaque mesure vers le measure_id exact (match normalisé id/label) ; tolère apostrophes/casse."""
        cat = self.measures(dataset)
        ids = {m["id"] for m in cat}
        bynorm: dict[str, set] = {}
        for m in cat:
            bynorm.setdefault(_norm(m["id"]), set()).add(m["id"])
            bynorm.setdefault(_norm(m.get("label") or ""), set()).add(m["id"])
        out = []
        for m in measures:
            if m in ids:
                out.append(m)
                continue
            cand = bynorm.get(_norm(m)) or set()
            if len(cand) == 1:
                resolved = next(iter(cand))
                logger.info("RPE : mesure résolue %r → %r", m, resolved)
                out.append(resolved)
            else:
                out.append(m)  # laissé tel quel → présence 1.0 + avertissement
        return out

    def query(
        self,
        dataset: str,
        dimensions: list,
        measures: Optional[list] = None,
        filters: Optional[dict] = None,
        ddvars: Optional[dict] = None,
    ) -> list[dict]:
        """Requête getCubeResult arbitraire ; renvoie des lignes tidy (mesure, dimensions, période, valeur)."""
        key = self._key(dataset)
        tpl = _RES["datasets"][key]
        cubeid = self.cubeids.get(key)
        if not cubeid:
            raise RpeLoginError(f"cubeId inconnu pour {dataset} — lancer refresh_catalog()")
        if measures is None:
            measures = [m["id"] for m in self.measures(dataset)]
        else:
            measures = self._resolve_measures(dataset, list(measures))

        dims = [d if isinstance(d, dict) else {"dim": d, "hPos": -1, "lPos": -1} for d in dimensions]
        sel = json.loads(json.dumps(tpl["sel"]))
        sel["dimsToExplore"] = [
            {
                "dim": d["dim"],
                "enabled": True,
                "hPos": d.get("hPos", -1),
                "lPos": d.get("lPos", -1),
                "format": d.get("format"),
                "displayMode": 0,
            }
            for d in dims
        ]
        n = len(dims)
        sel["axis"] = [None] + [[i] for i in range(n)]
        sel["pivot"] = 0
        sel["measureAxis"] = 0
        nm = len(measures)
        sel["measuresToKeep"] = list(measures)
        sel["targetsForMeasure"] = [None] * nm
        sel["aggsForMeasure"] = [-1] * nm
        sel["fmtsForMeasure"] = [None] * nm
        sel["measuresToKeepHidden"] = [False] * nm
        sel["measuresToKeepHiddenLabel"] = [False] * nm
        if filters is not None:
            # Why: filtre niveau 0 uniquement — non fiable sur une dimension hiérarchique (géo).
            # Pour la géo, ventiler par la dimension et filtrer les lignes du résultat (cf. SKILL --where).
            sel["dimsToFilter"] = [
                {"dim": d, "hierarchy": 0, "level": 0, "selectedMembers": list(codes), "mode": 0}
                for d, codes in filters.items()
            ]
        for v in sel.get("ddVars", []):
            if ddvars and v["name"] in ddvars:
                v["cur"] = ddvars[v["name"]]

        params = {
            "method": "getCubeResult",
            "cubeid": cubeid,
            "frameId": tpl["frameId"],
            "pageId": tpl["pageId"],
            "sel": json.dumps(sel, ensure_ascii=False),
        }
        rows = self._parse(dataset, sel, self._post_file(params).json(), n)
        if rows and not any(r.get("measure_id") for r in rows):
            logger.warning(
                "RPE query : aucune mesure reconnue (valeurs de présence 1.0) — vérifier measure_id dans rpe_measure"
            )
        return rows

    def _post_file(self, params: dict) -> httpx.Response:
        headers = {"User-Agent": UA, "X-Requested-With": "XMLHttpRequest", "Referer": REFERER}
        r = self.http.post(BASE + "/file", data=params, headers=headers, timeout=TIMEOUT)
        if r.status_code == 403:  # session expirée → re-login puis nouvel essai
            self._relogin()
            r = self.http.post(BASE + "/file", data=params, headers=headers, timeout=TIMEOUT)
        r.raise_for_status()
        return r

    def _gwt(self, payload: str) -> str:
        headers = _gwt_headers(BAKED_PERMUTATION)
        r = self.http.post(
            MODULE + "dash", content=_SID_RE.sub(self.sid or "", payload), headers=headers, timeout=TIMEOUT
        )
        if not _ok(r):  # session expirée → re-login puis nouvel essai
            self._relogin()
            r = self.http.post(
                MODULE + "dash", content=_SID_RE.sub(self.sid or "", payload), headers=headers, timeout=TIMEOUT
            )
        return r.text if r.status_code == 200 else ""

    @staticmethod
    def _parse(dataset: str, sel: dict, body: dict, ndims: int) -> list[dict]:
        axis = body.get("axis") or []
        meas = axis[0] if axis else []
        dim_axes = axis[1 : 1 + ndims]
        headers = body.get("dimsAndMeasuresHeaders") or []
        rows = []
        for ln in body.get("lines") or []:
            if len(ln) < 2 + ndims:
                continue
            m = meas[ln[0]] if isinstance(ln[0], int) and ln[0] < len(meas) else {}
            row = {"dataset": dataset, "measure": m.get("f") or m.get("i"), "measure_id": m.get("i"), "value": ln[-1]}
            for k in range(ndims):
                di = ln[1 + k]
                members = dim_axes[k] if k < len(dim_axes) else []
                mem = members[di] if isinstance(di, int) and di < len(members) else {}
                name = headers[k] if k < len(headers) else f"dim{k}"
                row[name] = mem.get("f") or mem.get("i")
                row[name + "_code"] = mem.get("i")
                if k == 0:
                    row["dimension"] = name
                    row["member_code"] = mem.get("i")
                    row["member_label"] = mem.get("f") or mem.get("i")
                    row["period"] = _period_of(sel, name, mem)
            rows.append(row)
        return rows

    def refresh_catalog(self) -> dict:
        """Rafraîchit les cubeIds (qui tournent au rebuild) via getFlowsView ; renvoie {cube_key: cube_id}."""
        self._gwt(_RES["gwt"]["getUserParams"])
        self._gwt(_RES["gwt"]["loadWallet"])
        found = set()
        for payload in _RES["gwt"]["getFlowsView"]:
            found.update(_CUBE_RE.findall(self._gwt(payload)))
        fresh = {cube.split("_")[0]: cube for cube in found}
        self.cubeids.update(fresh)
        logger.info("refresh_catalog : %d cubeIds rafraîchis", len(fresh))
        return fresh

    def mirror(self, dimensions: Optional[list] = None) -> list[dict]:
        """Cache des « données faciles » : marginales par défaut (géo niveau Région + temps) pour chaque dataset."""
        rows: list[dict] = []
        for key, tpl in _RES["datasets"].items():
            if key not in self.cubeids:
                continue
            name = tpl["cubeName"]
            for dim in dimensions or _default_mirror_dims(self.dimensions(name)):
                try:
                    rows.extend(self.query(name, [dim]))
                except (httpx.HTTPError, KeyError) as e:
                    logger.warning("mirror : échec %s / %s : %s", name, dim, e)
        logger.info("mirror : %d lignes collectées", len(rows))
        return rows


# Niveaux géographiques (dim hiérarchique C_TERRITOIRE_ID) ; codes INSEE alignés région/dépt, CLPE pour le territoire.
GEO_LEVELS = {
    "Région": {"dim": "C_TERRITOIRE_ID", "hPos": 0, "lPos": 1},  # ~19
    "Département": {"dim": "C_TERRITOIRE_ID", "hPos": 0, "lPos": 0},  # ~111
    "CLPE": {"dim": "C_TERRITOIRE_ID", "hPos": -1, "lPos": -1},  # ~363 (territoire feuille)
}
# Couverture géo matérialisée chaque nuit par le mirror (configurable).
MIRROR_GEO = ["Région", "Département", "CLPE"]


def _default_mirror_dims(dims: list[dict]) -> list:
    has_terr = any(d["id"] == "C_TERRITOIRE_ID" for d in dims)
    out = [GEO_LEVELS[g] for g in MIRROR_GEO if has_terr]
    out += [
        {"dim": d["id"], "hPos": 0, "lPos": 0, "format": {"id": "Mois Annee"}}
        for d in dims
        if d.get("time") and d["id"].startswith("D_DATE")
    ]
    return out


def store_catalog(client: RpeClient, fresh_cubeids: dict) -> None:
    eng = get_engine()
    cat = _RES["catalog"]
    with eng.begin() as conn:
        conn.execute(delete(rpe_theme))
        conn.execute(delete(rpe_dataset))
        conn.execute(delete(rpe_dimension))
        conn.execute(delete(rpe_measure))
        roles = {c.get("roleId") for c in cat.values() if c.get("roleId")}
        if roles:
            conn.execute(insert(rpe_theme), [{"role_id": r, "name": r} for r in roles])
        conn.execute(
            insert(rpe_dataset),
            [
                {
                    "cube_key": k,
                    "name": c["cubeName"],
                    "cube_id": fresh_cubeids.get(k, c.get("cubeId")),
                    "role_id": c.get("roleId"),
                }
                for k, c in cat.items()
            ],
        )
        dims = [
            {
                "dataset": c["cubeName"],
                "dim_id": d["id"],
                "name": d["name"],
                "category": d.get("category"),
                "caption_dim": d.get("captionDim"),
                "n_members": d.get("nbMembers"),
            }
            for c in cat.values()
            for d in c["dimensions"]
        ]
        if dims:
            conn.execute(insert(rpe_dimension), dims)
        meas = [
            {"dataset": c["cubeName"], "measure_id": m["id"], "label": m["label"]}
            for c in cat.values()
            for m in c["measures"]
        ]
        if meas:
            conn.execute(insert(rpe_measure), meas)


def update_measure_labels(rows: list[dict]) -> int:
    """Rafraîchit les libellés de mesures (id→label) à partir des réponses getCubeResult (axis[0])."""
    pairs = {(r["dataset"], r["measure_id"]): r["measure"] for r in rows if r.get("measure_id")}
    if not pairs:
        return 0
    payload = [{"dataset": d, "measure_id": mid, "label": label} for (d, mid), label in pairs.items()]
    stmt = pg_insert(rpe_measure).values(payload)
    stmt = stmt.on_conflict_do_update(index_elements=["dataset", "measure_id"], set_={"label": stmt.excluded.label})
    with get_engine().begin() as conn:
        conn.execute(stmt)
    return len(payload)


def store_facts(rows: list[dict]) -> int:
    if not rows:
        return 0
    cols = ("dataset", "measure", "measure_id", "period", "dimension", "member_code", "member_label", "value")
    payload = [{c: r.get(c) for c in cols} for r in rows if "member_code" in r]
    eng = get_engine()
    datasets = {r["dataset"] for r in payload}
    with eng.begin() as conn:
        for ds in datasets:
            conn.execute(delete(rpe_fact).where(rpe_fact.c.dataset == ds))
        if payload:
            conn.execute(insert(rpe_fact), payload)
    return len(payload)


def refresh() -> dict:
    """Point d'entrée cron : login → catalogue → cache données faciles → persistance matometa. Alerte en cas d'échec."""
    ensure_schema()
    try:
        client = RpeClient.connect()
    except RpeLoginError as e:
        notify_alert_channel(f"RPE refresh : login impossible ({e})")
        raise
    try:
        fresh = client.refresh_catalog()
        store_catalog(client, fresh)
        rows = client.mirror()
        labels = update_measure_labels(rows)
        n = store_facts(rows)
    except (httpx.HTTPError, ValueError) as e:
        notify_alert_channel(f"RPE refresh : échec rafraîchissement ({e})")
        raise
    finally:
        client.close()
    logger.info("RPE refresh terminé : %d cubeIds, %d libellés, %d lignes de faits", len(fresh), labels, n)
    return {"cubeids": len(fresh), "labels": labels, "facts": n}
