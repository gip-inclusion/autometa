"""Client du tableau de bord RPE (France Travail / DigDash) : login, requêtes à la demande, catalogue. httpx pur."""

import copy
import json
import logging
import re
import time
from collections import defaultdict
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from urllib.parse import quote

import httpx
from sqlalchemy import JSON, Column, DateTime, Integer, MetaData, String, Table, delete, insert, select, text
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
    render_gwt,
)
from web import config
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
SCHEMA = "dashboard_storage"
SESSION_TTL_S = 1200  # < 30 min Tomcat idle ; un 403 déclenche de toute façon un re-login

_SID_RE = re.compile(r"4c9184f37cff01[0-9a-f]+")
CUBE_RE = re.compile(r"[0-9a-f]{32}_[0-9a-f]{32}_[0-9a-f]+_[0-9]{13}")
_HEX32_RE = re.compile(r"[0-9A-F]{32}")


class RpeLoginError(RuntimeError):
    """Login RPE impossible (identifiants ou valeurs de build GWT obsolètes)."""


@dataclass
class Signatures:
    permutation: str
    strong_name: str
    policy_login: str
    policy_dash: str
    public_pass: str


def load_signature_row() -> dict | None:
    try:
        eng = get_engine()
        with eng.connect() as conn:
            if not eng.dialect.has_table(conn, "rpe_signature", schema=SCHEMA):
                return None
            row = conn.execute(select(rpe_signature).where(rpe_signature.c.id == 1)).mappings().first()
    except SQLAlchemyError as e:
        logger.warning("RPE : lecture signature DB impossible (%s)", e)
        return None
    return dict(row) if row else None


def store_signature(sigs: Signatures, sid: str | None, jsessionid: str | None, bundle_nocache: str | None) -> None:
    payload = {
        "id": 1,
        "permutation": sigs.permutation,
        "strong_name": sigs.strong_name,
        "policy_login": sigs.policy_login,
        "policy_dash": sigs.policy_dash,
        "sid": sid,
        "jsessionid": jsessionid,
        "bundle_nocache": bundle_nocache,
        "validated_at": datetime.now(timezone.utc),
    }
    stmt = pg_insert(rpe_signature).values(payload)
    stmt = stmt.on_conflict_do_update(index_elements=["id"], set_={k: payload[k] for k in payload if k != "id"})
    with get_engine().begin() as conn:
        conn.execute(stmt)


def load_signatures() -> Signatures:
    """Signatures GWT : DB d'abord (dashboard_storage.rpe_signature), repli ENV. Mot de passe toujours depuis l'ENV."""
    row = load_signature_row()
    if row and all(row.get(k) for k in ("permutation", "strong_name", "policy_login", "policy_dash")):
        return Signatures(
            row["permutation"], row["strong_name"], row["policy_login"], row["policy_dash"], config.RPE_PUBLIC_PASS
        )
    return Signatures(
        config.RPE_PERMUTATION,
        config.RPE_STRONG_NAME,
        config.RPE_POLICY_LOGIN,
        config.RPE_POLICY_DASH,
        config.RPE_PUBLIC_PASS,
    )


_metadata = MetaData(schema=SCHEMA)
rpe_signature = Table(
    "rpe_signature",
    _metadata,
    Column("id", Integer, primary_key=True),
    Column("permutation", String),
    Column("strong_name", String),
    Column("policy_login", String),
    Column("policy_dash", String),
    Column("sid", String),
    Column("jsessionid", String),
    Column("bundle_nocache", String),
    Column("validated_at", DateTime(timezone=True)),
)
rpe_toc = Table(
    "rpe_toc",
    _metadata,
    Column("cube_key", String, primary_key=True),
    Column("cube_id", String),
    Column("name", String),
    Column("measures", JSON),
    Column("dimensions", JSON),
    Column("territory_codes", JSON),
    Column("charts", JSON),
    Column("refreshed_at", DateTime(timezone=True)),
)


def ensure_schema() -> None:
    eng = get_engine()
    with eng.begin() as conn:
        conn.execute(text("CREATE SCHEMA IF NOT EXISTS " + SCHEMA))
    _metadata.create_all(eng)


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


def _attempt_login(sigs: Signatures, timeout: int = TIMEOUT) -> httpx.Client | None:
    client = httpx.Client(headers={"User-Agent": UA}, timeout=timeout)
    headers = _gwt_headers(sigs.permutation)

    def gwt(payload: str) -> httpx.Response:
        body = render_gwt(
            payload,
            strong_name=sigs.strong_name,
            policy_login=sigs.policy_login,
            policy_dash=sigs.policy_dash,
            public_pass=sigs.public_pass,
        )
        return client.post(MODULE + "dash", content=body, headers=headers, timeout=timeout)

    settings = gwt(GWT["getUserSettings"])
    login_resp = gwt(GWT["login"])
    if _ok(settings) and _ok(login_resp):
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


def login(sigs: Signatures) -> tuple[httpx.Client, Signatures]:
    """Session authentifiée (httpx) + les Signatures retenues ; re-scrape permutation/strong_name et réessaie si échec."""
    client = _attempt_login(sigs)
    if client is not None:
        return client, sigs
    logger.warning("RPE login échoué avec les signatures courantes, re-scraping en cours")
    for permutation, strong_name in _scrape_builds():
        candidate = replace(sigs, permutation=permutation, strong_name=strong_name)
        client = _attempt_login(candidate)
        if client is not None:
            logger.info("RPE login réussi via build re-scrapé permutation=%s", permutation)
            return client, candidate
    raise RpeLoginError("login impossible — identifiants ou valeurs de build GWT (strong-name/permutation) obsolètes")


def check_connectivity(timeout: int = TIMEOUT) -> tuple[bool, str]:
    """Connectivité RPE avec les signatures courantes, sans re-scrape (pour le selftest)."""
    try:
        client = _attempt_login(load_signatures(), timeout=timeout)
    except httpx.HTTPError as e:
        return False, f"injoignable : {e}"
    if client is None:
        return False, "login refusé (signatures GWT périmées ?)"
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

    def __init__(self, http: httpx.Client, sigs: Signatures, sid: str | None = None):
        self.http = http
        self.sigs = sigs
        self.sid = sid or self._resolve_sid()
        self.bundle_nocache = None
        self.catalog = self._load_catalog()
        self.cubeids = self._load_cubeids()

    @classmethod
    def connect(cls) -> "RpeClient":
        """Réutilise la session en cache si fraîche, sinon login httpx (un 403 ultérieur relance un login)."""
        sigs = load_signatures()
        row = load_signature_row()
        if row and row.get("jsessionid"):
            age = (
                (datetime.now(timezone.utc) - row["validated_at"]).total_seconds() if row.get("validated_at") else None
            )
            if age is not None and age <= SESSION_TTL_S:
                http = httpx.Client(
                    headers={"User-Agent": UA},
                    cookies={"JSESSIONID": row["jsessionid"], "digdashSessionId": row.get("sid") or ""},
                    timeout=TIMEOUT,
                )
                return cls(http, sigs, sid=row.get("sid"))
        http, sigs = login(sigs)
        inst = cls(http, sigs)
        store_signature(sigs, inst.sid, http.cookies.get("JSESSIONID"), inst.bundle_nocache)
        return inst

    def _relogin(self) -> None:
        self.http.close()
        self.http, self.sigs = login(self.sigs)
        self.sid = self._resolve_sid()
        store_signature(self.sigs, self.sid, self.http.cookies.get("JSESSIONID"), self.bundle_nocache)

    def close(self) -> None:
        self.http.close()

    def _prep(self, payload: str) -> str:
        """Substitue les signatures GWT courantes (re-scrapées au besoin) + le sid dans un payload GWT."""
        rendered = render_gwt(
            payload,
            strong_name=self.sigs.strong_name,
            policy_login=self.sigs.policy_login,
            policy_dash=self.sigs.policy_dash,
            public_pass=self.sigs.public_pass,
        )
        return _SID_RE.sub(self.sid or "", rendered)

    def _resolve_sid(self) -> str | None:
        sid = self.http.cookies.get("digdashSessionId")
        if sid:
            return sid
        body = render_gwt(
            GWT["getUserSettings"],
            strong_name=self.sigs.strong_name,
            policy_login=self.sigs.policy_login,
            policy_dash=self.sigs.policy_dash,
            public_pass=self.sigs.public_pass,
        )
        r = self.http.post(MODULE + "dash", content=body, headers=_gwt_headers(self.sigs.permutation), timeout=TIMEOUT)
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
        territory: tuple | None = None,
        ddvars: dict | None = None,
        timeout: int = TIMEOUT,
    ) -> list[dict]:
        """Requête getCubeResult ; lignes tidy. `territory=(palier, codes)` filtre la géo serveur au bon niveau ; `filters` = autres dims (niveau 0)."""
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
        if filters is not None or territory is not None:
            # Why: redéfinir dimsToFilter (même vide) lève le filtre de période figé par le template.
            dims_to_filter = []
            if territory is not None:
                palier, codes = territory
                dims_to_filter.append({
                    "dim": "C_TERRITOIRE_ID",
                    "hierarchy": 0,
                    "level": GEO_LEVELS[palier]["lPos"],  # palier hiérarchique : région 1, dépt 0, CLPE -1
                    "selectedMembers": list(codes),
                    "mode": 0,
                })
            if filters:
                # Why: la géo est hiérarchique (niveau par palier, cf. territory=) ; la filtrer ici la
                # matcherait au niveau 0 quel que soit le code → valeurs silencieusement fausses.
                if "C_TERRITOIRE_ID" in filters:
                    raise ValueError(
                        "filtrer la géo via territory=(palier, codes), pas filters (niveau hiérarchique requis)"
                    )
                dims_to_filter += [
                    {"dim": d, "hierarchy": 0, "level": 0, "selectedMembers": list(codes), "mode": 0}
                    for d, codes in filters.items()
                ]
            sel["dimsToFilter"] = dims_to_filter
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
            MODULE + "dash", content=self._prep(payload), headers=_gwt_headers(self.sigs.permutation), timeout=TIMEOUT
        )
        if not _ok(r):  # session/build périmé → re-login (re-scrape éventuel) puis nouvel essai
            self._relogin()
            r = self.http.post(
                MODULE + "dash",
                content=self._prep(payload),
                headers=_gwt_headers(self.sigs.permutation),
                timeout=TIMEOUT,
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

    def mirror(self, dimensions: list | None = None, budget_s: float | None = None) -> tuple[list[dict], list[str]]:
        """Cache séquentiel des « données faciles » (marginales géo + temps), borné en temps. Renvoie (lignes, échecs)."""
        # Why: serveur public PARTAGÉ avec les requêtes live et qui SÉRIALISE les appels → séquentiel (paralléliser
        # ne fait qu'allonger les délais et multiplier les timeouts, cf. skills/rpe/SKILL.md) et borné par budget_s,
        # bien sous le timeout du cron : le cron FINIT et libère le serveur, quitte à cacher moins. Cube froid
        # injoignable → échec sans réessai (le serveur ne sait pas le calculer).
        deadline = time.monotonic() + (MIRROR_BUDGET_S if budget_s is None else budget_s)
        rows: list[dict] = []
        failed: list[str] = []
        stopped = False
        for key, cat in self.catalog.items():
            if stopped:
                break
            if key not in self.cubeids:
                continue
            name = cat["cubeName"]
            plan = [(None, d) for d in dimensions] if dimensions else mirror_plan(self.dimensions(name))
            for label, spec in plan:
                if time.monotonic() >= deadline:
                    stopped = True
                    break
                try:
                    r = self.query(name, [spec], timeout=MIRROR_TIMEOUT)
                    if label:  # libellé géo canonique (Région/Département/CLPE), découplé du header serveur
                        for x in r:
                            x["dimension"] = label
                    rows.extend(r)
                except (httpx.HTTPError, KeyError) as e:
                    failed.append(f"{name} / {label or spec.get('dim')}")
                    logger.warning("mirror : échec %s : %s", failed[-1], e)
        if stopped:
            logger.warning("mirror : budget temps atteint, arrêt anticipé (serveur libéré pour les requêtes live)")
        logger.info("mirror : %d lignes, %d échecs", len(rows), len(failed))
        return rows, failed

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
MIRROR_TIMEOUT = 30  # fail-fast par appel (cube froid > ~20s = injoignable côté serveur) ; pas de réessai
MIRROR_BUDGET_S = 360  # borne globale du mirror, bien sous le timeout cron (600s) : il s'arrête et persiste ce qu'il a


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
