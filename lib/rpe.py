"""Client du tableau de bord RPE (France Travail / DigDash) : login, requêtes à la demande, catalogue. httpx pur."""

import copy
import json
import logging
import re
import threading
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from urllib.parse import quote

import httpx
from sqlalchemy import ARRAY, Column, DateTime, Float, Integer, MetaData, String, Table, delete, insert, select, text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.exc import SQLAlchemyError

from lib.rpe_gwt import (
    GWT,
    SEL,
    build_flowsview_payload,
    cube_dm_urls,
    extract_frame_ids,
    flowsview_header,
    parse_charts,
    parse_cube_dm,
)
from web.alerts import notify_alert_channel
from web.config import RPE_PUBLIC_PASS
from web.db import get_engine

logger = logging.getLogger(__name__)

# Données publiques du tableau de bord en accès libre (identifiants présents dans l'URL publique).
HOST = "https://pilotage-rpe.francetravail.org"
BASE = HOST + "/digdash_dashboard"
MODULE = BASE + "/dashboard/"
PUBLIC_PASS = RPE_PUBLIC_PASS
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0 Safari/537.36"
REFERER = BASE + "/index.html?domain=ddenterpriseapi&user=public&pass=" + quote(PUBLIC_PASS, safe="")
TIMEOUT = 60
SCHEMA = "matometa"
SESSION_TTL_S = 1200  # < 30 min Tomcat idle ; un 403 déclenche de toute façon un re-login

# Valeurs liées au build GWT, re-scrapables en cas d'échec de login (cf. _scrape_builds).
BAKED_PERMUTATION = "2D1551B7C160B162D34A4CD10515557B"
BAKED_STRONG_NAME = "B28E527AF46D9C6155A876F4769EC2F4"

_SID_RE = re.compile(r"4c9184f37cff01[0-9a-f]+")
CUBE_RE = re.compile(r"[0-9a-f]{32}_[0-9a-f]{32}_[0-9a-f]+_[0-9]{13}")
_HEX32_RE = re.compile(r"[0-9A-F]{32}")


class RpeLoginError(RuntimeError):
    """Login RPE impossible (identifiants ou valeurs de build GWT obsolètes)."""


_metadata = MetaData(schema=SCHEMA)
rpe_dataset = Table(
    "rpe_dataset",
    _metadata,
    Column("cube_key", String, primary_key=True),
    Column("name", String),
    Column("cube_id", String),
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
rpe_chart = Table(
    "rpe_chart",
    _metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("chart_title", String),
    Column("cube_key", String),
    Column("cube_name", String),
    Column("measures_shown", ARRAY(String)),
    Column("dims_shown", ARRAY(String)),
)


def ensure_schema() -> None:
    eng = get_engine()
    with eng.begin() as conn:
        conn.execute(text("CREATE SCHEMA IF NOT EXISTS " + SCHEMA))
    _metadata.create_all(eng)


def load_cached_session() -> tuple[str, str] | None:
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


def save_session(jsessionid: str | None, sid: str | None) -> None:
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


def _attempt_login(permutation: str, strong_name: str, timeout: int = TIMEOUT) -> httpx.Client | None:
    client = httpx.Client(headers={"User-Agent": UA}, timeout=timeout)
    headers = _gwt_headers(permutation)

    def gwt(payload: str) -> httpx.Response:
        body = payload.replace(BAKED_STRONG_NAME, strong_name).replace("__RPE_PASS__", PUBLIC_PASS)
        return client.post(MODULE + "dash", content=body, headers=headers, timeout=timeout)

    settings = gwt(GWT["getUserSettings"])
    login = gwt(GWT["login"])
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


def login() -> tuple[httpx.Client, str, str]:
    """Session authentifiée (httpx) + le couple (permutation, strong_name) retenu ; re-scrape et réessaie si échec."""
    client = _attempt_login(BAKED_PERMUTATION, BAKED_STRONG_NAME)
    if client is not None:
        return client, BAKED_PERMUTATION, BAKED_STRONG_NAME
    logger.warning("RPE login échoué avec les valeurs de build par défaut, re-scraping en cours")
    for permutation, strong_name in _scrape_builds():
        client = _attempt_login(permutation, strong_name)
        if client is not None:
            logger.info("RPE login réussi via build re-scrapé permutation=%s", permutation)
            return client, permutation, strong_name
    raise RpeLoginError("login impossible — identifiants ou valeurs de build GWT (strong-name/permutation) obsolètes")


def check_connectivity(timeout: int = TIMEOUT) -> tuple[bool, str]:
    """Connectivité RPE avec les valeurs de build par défaut, sans re-scrape (pour le selftest)."""
    try:
        client = _attempt_login(BAKED_PERMUTATION, BAKED_STRONG_NAME, timeout=timeout)
    except httpx.HTTPError as e:
        return False, f"injoignable : {e}"
    if client is None:
        return False, "login refusé (valeurs de build par défaut périmées ?)"
    client.close()
    return True, "login OK"


def period_of(sel: dict, breakdown_dim: str, member: dict) -> str | None:
    if breakdown_dim and "ate" in breakdown_dim:  # "Date d'observation", "Mois d'entrée…"
        return member.get("f")
    for f in sel.get("dimsToFilter") or []:
        if str(f.get("dim", "")).startswith("D_DATE") and f.get("selectedMembers"):
            try:
                secs = int(f["selectedMembers"][0]) + 43200  # bornes de mois en Europe/Paris
            except TypeError, ValueError:
                continue
            return epoch_month(secs)
    return None


def epoch_month(secs: int) -> str:
    return datetime.fromtimestamp(secs, tz=timezone.utc).strftime("%Y-%m")


def norm(s: str) -> str:
    """Normalise pour le matching de mesure : minuscules, apostrophes unifiées, espaces compactés."""
    return " ".join((s or "").lower().replace("’", "'").replace("‘", "'").replace("´", "'").split())


class RpeClient:
    """Session RPE authentifiée : requêtes getCubeResult arbitraires + rafraîchissement catalogue."""

    def __init__(
        self,
        http: httpx.Client,
        permutation: str = BAKED_PERMUTATION,
        strong_name: str = BAKED_STRONG_NAME,
        sid: str | None = None,
    ):
        self.http = http
        self.permutation = permutation
        self.strong_name = strong_name
        self._relogin_lock = threading.Lock()
        self.sid = sid or self._resolve_sid()
        self.catalog = self._load_catalog()
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
        http, permutation, strong_name = login()
        inst = cls(http, permutation, strong_name)
        save_session(http.cookies.get("JSESSIONID"), inst.sid)
        return inst

    def _relogin(self) -> None:
        stale = self.http
        with self._relogin_lock:
            if self.http is not stale:  # Why: another thread already re-logged in under concurrency; reuse its session
                return
            self.http.close()
            self.http, self.permutation, self.strong_name = login()
            self.sid = self._resolve_sid()
            save_session(self.http.cookies.get("JSESSIONID"), self.sid)

    def close(self) -> None:
        self.http.close()

    def _prep(self, payload: str) -> str:
        """Substitue le strong-name courant (re-scrapé au besoin) + le sid dans un payload GWT."""
        return _SID_RE.sub(self.sid or "", payload.replace(BAKED_STRONG_NAME, self.strong_name))

    def _resolve_sid(self) -> str | None:
        sid = self.http.cookies.get("digdashSessionId")
        if sid:
            return sid
        body = GWT["getUserSettings"].replace(BAKED_STRONG_NAME, self.strong_name).replace("__RPE_PASS__", PUBLIC_PASS)
        r = self.http.post(MODULE + "dash", content=body, headers=_gwt_headers(self.permutation), timeout=TIMEOUT)
        m = _SID_RE.search(r.text)
        if not m:
            logger.warning(
                "RPE : sid de session introuvable (statut %s) — requêtes ultérieures risquent un 403", r.status_code
            )
            return None
        return m.group(0)

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
            logger.warning("RPE : cubeIds DB indisponibles (%s)", e)
        return cubeids

    def _load_catalog(self) -> dict:
        """Catalogue {cube_key: {cubeName, dimensions, measures}} depuis la DB (vide tant que le cron n'a pas tourné)."""
        catalog: dict = {}
        try:
            eng = get_engine()
            with eng.connect() as conn:
                if not eng.dialect.has_table(conn, "rpe_dataset", schema=SCHEMA):
                    return catalog
                names = {r.cube_key: r.name for r in conn.execute(select(rpe_dataset.c.cube_key, rpe_dataset.c.name))}
                dims: dict[str, list] = defaultdict(list)
                for r in conn.execute(select(rpe_dimension)):
                    dims[r.dataset].append({
                        "id": r.dim_id,
                        "name": r.name,
                        "category": r.category,
                        "captionDim": r.caption_dim,
                        "nbMembers": r.n_members,
                    })
                meas: dict[str, list] = defaultdict(list)
                for r in conn.execute(select(rpe_measure)):
                    meas[r.dataset].append({"id": r.measure_id, "label": r.label})
        except SQLAlchemyError as e:
            logger.warning("RPE : catalogue DB indisponible (%s)", e)
            return catalog
        for cube_key, name in names.items():
            catalog[cube_key] = {"cubeName": name, "dimensions": dims.get(name, []), "measures": meas.get(name, [])}
        return catalog

    def _key(self, dataset: str) -> str:
        if dataset in self.catalog:
            return dataset
        for key, d in self.catalog.items():
            if d["cubeName"] == dataset:
                return key
        raise KeyError(f"dataset inconnu : {dataset}")

    def datasets(self) -> list[str]:
        return [d["cubeName"] for d in self.catalog.values()]

    def measures(self, dataset: str) -> list[dict]:
        return self.catalog[self._key(dataset)]["measures"]

    def dimensions(self, dataset: str) -> list[dict]:
        return self.catalog[self._key(dataset)]["dimensions"]

    def _resolve_measures(self, dataset: str, measures: list) -> list:
        """Résout chaque mesure vers le measure_id exact (match normalisé id/label) ; tolère apostrophes/casse."""
        cat = self.measures(dataset)
        ids = {m["id"] for m in cat}
        bynorm: dict[str, set] = {}
        for m in cat:
            bynorm.setdefault(norm(m["id"]), set()).add(m["id"])
            bynorm.setdefault(norm(m.get("label") or ""), set()).add(m["id"])
        out = []
        for m in measures:
            if m in ids:
                out.append(m)
                continue
            cand = bynorm.get(norm(m)) or set()
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
        measures: list | None = None,
        filters: dict | None = None,
        ddvars: dict | None = None,
        timeout: int = TIMEOUT,
    ) -> list[dict]:
        """Requête getCubeResult ; lignes tidy. `filters` : valeur simple = niveau 0, ou dict {members, level} pour la géo hiérarchique."""
        key = self._key(dataset)
        cubeid = self.cubeids.get(key)
        if not cubeid:
            raise RpeLoginError(f"cubeId inconnu pour {dataset} — lancer refresh_catalog()")
        if measures is None:
            measures = [m["id"] for m in self.measures(dataset)]
        else:
            measures = self._resolve_measures(dataset, list(measures))

        dims = [d if isinstance(d, dict) else {"dim": d, "hPos": -1, "lPos": -1} for d in dimensions]
        sel = copy.deepcopy(SEL)
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
            # Why: valeur simple → filtre niveau 0 ; dict {"members","level"} pour la géo hiérarchique
            # (C_TERRITOIRE_ID : level = lPos du palier — Région 1, Département 0, CLPE -1 ; un mauvais
            # niveau renvoie des valeurs silencieusement fausses, cf. GEO_LEVELS).
            sel["dimsToFilter"] = []
            for d, v in filters.items():
                members = v["members"] if isinstance(v, dict) else v
                level = v["level"] if isinstance(v, dict) else 0
                sel["dimsToFilter"].append({
                    "dim": d,
                    "hierarchy": 0,
                    "level": level,
                    "selectedMembers": list(members),
                    "mode": 0,
                })
        for v in sel.get("ddVars", []):
            if ddvars and v["name"] in ddvars:
                v["cur"] = ddvars[v["name"]]

        params = {
            "method": "getCubeResult",
            "cubeid": cubeid,
            "frameId": "",  # Why: vestigial — getCubeResult n'utilise que cubeid + sel (vérifié en spike)
            "pageId": "",
            "sel": json.dumps(sel, ensure_ascii=False),
        }
        rows = self._parse(dataset, sel, self._post_file(params, timeout).json(), n)
        if rows and not any(r.get("measure_id") for r in rows):
            logger.warning(
                "RPE query : aucune mesure reconnue (valeurs de présence 1.0) — vérifier measure_id dans rpe_measure"
            )
        return rows

    def _post_file(self, params: dict, timeout: int = TIMEOUT) -> httpx.Response:
        headers = {"User-Agent": UA, "X-Requested-With": "XMLHttpRequest", "Referer": REFERER}
        r = self.http.post(BASE + "/file", data=params, headers=headers, timeout=timeout)
        if r.status_code == 403:  # session expirée → re-login puis nouvel essai
            self._relogin()
            r = self.http.post(BASE + "/file", data=params, headers=headers, timeout=timeout)
        r.raise_for_status()
        return r

    def _gwt(self, payload: str) -> str:
        r = self.http.post(
            MODULE + "dash", content=self._prep(payload), headers=_gwt_headers(self.permutation), timeout=TIMEOUT
        )
        if not _ok(r):  # session/build périmé → re-login (re-scrape éventuel) puis nouvel essai
            self._relogin()
            r = self.http.post(
                MODULE + "dash", content=self._prep(payload), headers=_gwt_headers(self.permutation), timeout=TIMEOUT
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
                    row["period"] = period_of(sel, name, mem)
            rows.append(row)
        return rows

    def refresh_catalog(self) -> tuple[dict, str]:
        """Rafraîchit tous les cubeIds via getFlowsView (tous les frames du wallet) ; renvoie (cubeids, réponse brute)."""
        self._gwt(GWT["getUserParams"])
        wallet = self._gwt(GWT["loadWallet"])
        header = flowsview_header(GWT["getFlowsView"])
        resp = self._gwt(build_flowsview_payload(extract_frame_ids(wallet), header))
        fresh = {cube.split("_")[0]: cube for cube in CUBE_RE.findall(resp)}
        self.cubeids.update(fresh)
        logger.info("refresh_catalog : %d cubeIds rafraîchis", len(fresh))
        return fresh, resp

    def mirror(self, dimensions: list | None = None, max_workers: int = 4) -> tuple[list[dict], list[str]]:
        """Cache des « données faciles » en parallèle borné ; les marginales géo trop lourdes sont ventilées par région."""
        # Why: serveur public → concurrence ≤ max_workers (il sérialise de toute façon). Une marginale géo d'un cube
        # lourd dépasse le timeout en bloc, mais filtrée sur une seule région elle revient vite : on la ventile alors
        # par région (codes dérivés des marginales légères du 1er tour) et on concatène. Marginale temps non
        # ventilable (le filtre région change la sémantique) → simple réessai. 5xx/parsing = définitifs.
        tasks: list[tuple[str, str | None, dict, str | None]] = []
        for key, cat in self.catalog.items():
            if key not in self.cubeids:
                continue
            name = cat["cubeName"]
            plan = [(None, d) for d in dimensions] if dimensions else mirror_plan(self.dimensions(name))
            tasks.extend((name, label, spec, None) for label, spec in plan)

        rows: list[dict] = []
        failed: list[str] = []
        batch_rows, timed_out, permanent = self._mirror_batch(tasks, max_workers)
        rows.extend(batch_rows)
        failed.extend(permanent)

        region_codes = sorted({
            x["member_code"] for x in batch_rows if x.get("dimension") == "Région" and x.get("member_code")
        })
        round2: list[tuple[str, str | None, dict, str | None]] = []
        for task in timed_out:
            name, label, spec, region = task
            if label is not None and region is None and region_codes:  # marginale géo nommée → ventiler par région
                round2.extend((name, label, spec, code) for code in region_codes)
            else:  # marginale temps / sous-tâche déjà filtrée / pas de codes région → simple réessai
                round2.append(task)
        if round2:
            batch_rows, timed_out2, permanent2 = self._mirror_batch(round2, max_workers)
            rows.extend(batch_rows)
            failed.extend(permanent2)
            failed.extend(self._task_label(t) for t in timed_out2)

        logger.info("mirror : %d lignes, %d échecs", len(rows), len(failed))
        return rows, failed

    def _mirror_batch(
        self, tasks: list[tuple[str, str | None, dict, str | None]], max_workers: int
    ) -> tuple[list[dict], list[tuple[str, str | None, dict, str | None]], list[str]]:
        """Lot de tâches mirror en parallèle ; renvoie (lignes, tâches en timeout, échecs définitifs)."""
        rows: list[dict] = []
        timed_out: list[tuple[str, str | None, dict, str | None]] = []
        permanent: list[str] = []
        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            futures = {pool.submit(self._mirror_one, task): task for task in tasks}
            for future in as_completed(futures):
                task = futures[future]
                try:
                    rows.extend(future.result())
                except httpx.TimeoutException as e:
                    timed_out.append(task)
                    logger.warning("mirror : timeout %s : %s", self._task_label(task), e)
                except (httpx.HTTPError, KeyError) as e:
                    permanent.append(self._task_label(task))
                    logger.warning("mirror : échec %s : %s", self._task_label(task), e)
        return rows, timed_out, permanent

    def _mirror_one(self, task: tuple[str, str | None, dict, str | None]) -> list[dict]:
        name, label, spec, region = task
        # Why: ventilation par région = filtre serveur C_TERRITOIRE_ID au niveau région (lPos), cf. GEO_LEVELS.
        filters = {"C_TERRITOIRE_ID": {"members": [region], "level": GEO_LEVELS["Région"]["lPos"]}} if region else None
        r = self.query(name, [spec], filters=filters, timeout=MIRROR_TIMEOUT)
        if label:  # libellé géo canonique (Région/Département/CLPE), découplé du header serveur
            for x in r:
                x["dimension"] = label
        return r

    @staticmethod
    def _task_label(task: tuple[str, str | None, dict, str | None]) -> str:
        name, label, spec, region = task
        base = f"{name} / {label or spec.get('dim')}"
        return f"{base} [{region}]" if region else base

    def fetch_cube_dm(self, url: str, timeout: int = TIMEOUT) -> str:
        """Télécharge un cube_dm (catalogue d'un cube) ; identifiants publics en query (cookies → 401 sur /ddenterpriseapi)."""
        full = HOST + url + "&user=public&pass=" + quote(PUBLIC_PASS, safe="")
        r = self.http.get(full, headers={"User-Agent": UA, "Referer": REFERER}, timeout=timeout)
        r.raise_for_status()
        return r.text


# Niveaux géographiques (dim hiérarchique C_TERRITOIRE_ID) ; codes INSEE alignés région/dépt, CLPE pour le territoire.
GEO_LEVELS = {
    "Région": {"dim": "C_TERRITOIRE_ID", "hPos": 0, "lPos": 1},  # ~19
    "Département": {"dim": "C_TERRITOIRE_ID", "hPos": 0, "lPos": 0},  # ~111
    "CLPE": {"dim": "C_TERRITOIRE_ID", "hPos": -1, "lPos": -1},  # ~363 (territoire feuille)
}
# Couverture géo matérialisée chaque nuit par le mirror (configurable).
MIRROR_GEO = ["Région", "Département", "CLPE"]
MIRROR_TIMEOUT = 45  # borne par appel mirror (cube froid ~1-20s), pour ne pas faire exploser le budget cron


def mirror_plan(dims: list[dict]) -> list[tuple[str | None, dict]]:
    """Plan de ventilation du mirror : (libellé canonique | None, spec de dimension). Géo nommée, temps brut."""
    has_terr = any(d["id"] == "C_TERRITOIRE_ID" for d in dims)
    plan: list[tuple[str | None, dict]] = [(g, GEO_LEVELS[g]) for g in MIRROR_GEO] if has_terr else []
    # Why: `time` n'est présent que sur le catalogue fraîchement dérivé (refresh) ; le mirror tourne
    # toujours sur ce catalogue-là, jamais sur celui rechargé de la DB (qui n'a pas la colonne time).
    plan += [
        (None, {"dim": d["id"], "hPos": 0, "lPos": 0, "format": {"id": "Mois Annee"}})
        for d in dims
        if d.get("time") and d["id"].startswith("D_DATE")
    ]
    return plan


def build_catalog(client: RpeClient, flows_response: str) -> tuple[dict, int]:
    """Catalogue {cube_key: {cubeName, dimensions, measures}} httpx + nb de cube_dm en échec (dims via cube_dm, mesures via graphes ; DDAudit exclus)."""
    measures_by_cube: dict[str, list] = defaultdict(list)
    seen: dict[str, set] = defaultdict(set)
    for ch in parse_charts(flows_response):
        for m in ch["measures_shown"]:
            if m not in seen[ch["cube_key"]]:
                seen[ch["cube_key"]].add(m)
                measures_by_cube[ch["cube_key"]].append({"id": m, "label": m})
    catalog: dict = {}
    failed = 0
    for cube_key, url in cube_dm_urls(flows_response).items():
        try:
            parsed = parse_cube_dm(client.fetch_cube_dm(url))
        except httpx.HTTPError as e:  # Why: ne pas logger e (l'URL porte le mot de passe public en clair)
            failed += 1
            logger.warning("build_catalog : cube_dm %s injoignable (%s)", cube_key, type(e).__name__)
            continue
        name = parsed["cube_name"]
        if not name or name.startswith("DDAudit"):  # cubes d'audit DigDash internes
            continue
        catalog[cube_key] = {
            "cubeName": name,
            "dimensions": [
                {
                    "id": d["id"],
                    "name": d["name"],
                    "category": d["category"],
                    "captionDim": d["caption_dim"],
                    "nbMembers": d["n_members"],
                    "time": d["time"],
                }
                for d in parsed["dimensions"]
            ],
            "measures": measures_by_cube.get(cube_key, []),
        }
    logger.info("build_catalog : %d datasets (hors DDAudit), %d cube_dm en échec", len(catalog), failed)
    return catalog, failed


def store_catalog(fresh_cubeids: dict, catalog: dict) -> int:
    """Remplacement complet du catalogue (dataset/dimension/measure). Catalogue vide → no-op (cache conservé)."""
    if not catalog:
        logger.warning("store_catalog : catalogue vide, cache inchangé")
        return 0
    eng = get_engine()
    with eng.begin() as conn:
        conn.execute(delete(rpe_dataset))
        conn.execute(delete(rpe_dimension))
        conn.execute(delete(rpe_measure))
        conn.execute(
            insert(rpe_dataset),
            [{"cube_key": k, "name": c["cubeName"], "cube_id": fresh_cubeids.get(k)} for k, c in catalog.items()],
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
            for c in catalog.values()
            for d in c["dimensions"]
        ]
        if dims:
            conn.execute(insert(rpe_dimension), dims)
        meas = [
            {"dataset": c["cubeName"], "measure_id": m["id"], "label": m["label"]}
            for c in catalog.values()
            for m in c["measures"]
        ]
        if meas:
            conn.execute(insert(rpe_measure), meas)
    return len(catalog)


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
    """Remplacement complet de `rpe_fact` si le mirror a produit des données (sinon on garde le cache précédent)."""
    cols = ("dataset", "measure", "measure_id", "period", "dimension", "member_code", "member_label", "value")
    payload = [{c: r.get(c) for c in cols} for r in rows if "member_code" in r]
    if not payload:  # mirror vide → ne pas vider le cache
        return 0
    with get_engine().begin() as conn:
        conn.execute(delete(rpe_fact))  # remplacement complet : aucune donnée périmée conservée
        conn.execute(insert(rpe_fact), payload)
    return len(payload)


def store_charts(records: list[dict], cube_names: dict) -> int:
    """Remplacement complet de `rpe_chart` (sinon on garde le cache). cube_names : {cube_key: cubeName}."""
    if not records:  # parse vide → ne pas vider le cache
        return 0
    payload = [
        {
            "chart_title": r["chart_title"],
            "cube_key": r["cube_key"],
            "cube_name": cube_names.get(r["cube_key"]),
            "measures_shown": r["measures_shown"],
            "dims_shown": r["dims_shown"],
        }
        for r in records
    ]
    with get_engine().begin() as conn:
        conn.execute(delete(rpe_chart))
        conn.execute(insert(rpe_chart), payload)
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
        fresh, flows = client.refresh_catalog()
        catalog, dm_failed = build_catalog(client, flows)
        client.catalog = catalog  # le mirror ventile sur le catalogue fraîchement dérivé (flag time inclus)
        cat_n = store_catalog(fresh, catalog)
        rows, failed = client.mirror()
        labels = update_measure_labels(rows)
        n = store_facts(rows)
        cube_names = {k: c["cubeName"] for k, c in catalog.items()}
        charts = store_charts(parse_charts(flows), cube_names)
    except (httpx.HTTPError, ValueError, SQLAlchemyError) as e:
        notify_alert_channel(f"RPE refresh : échec rafraîchissement ({type(e).__name__})")
        raise
    finally:
        client.close()
    if cat_n == 0:  # Why: aucun cube_dm parsé → format probablement changé ; cache catalogue conservé
        notify_alert_channel("RPE refresh : catalogue vide, cache inchangé")
    elif dm_failed:  # Why: catalogue partiel stocké → datasets potentiellement manquants, à investiguer
        notify_alert_channel(f"RPE refresh : catalogue partiel ({dm_failed} cube_dm injoignables)")
    if n == 0:  # remplacement non effectué → le cache sert des données périmées
        notify_alert_channel(f"RPE refresh : mirror vide, cache inchangé ({len(failed)} requêtes en échec)")
    if charts == 0 and flows:  # Why: getFlowsView a répondu mais aucun graphe parsé → format probablement changé
        notify_alert_channel("RPE refresh : aucun graphe parsé, rpe_chart inchangé")
    logger.info(
        "RPE refresh terminé : %d datasets, %d cubeIds, %d libellés, %d faits, %d graphes, %d échecs",
        cat_n,
        len(fresh),
        labels,
        n,
        charts,
        len(failed),
    )
    return {
        "datasets": cat_n,
        "cubeids": len(fresh),
        "labels": labels,
        "facts": n,
        "charts": charts,
        "failed": len(failed),
    }
