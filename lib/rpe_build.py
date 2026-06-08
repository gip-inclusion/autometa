"""Régénérateur browserless de rpe_templates.json : cubeIds frais + catalogue reporté, auto-validé."""

import json
import logging
import time
from pathlib import Path

import httpx

from lib.rpe import _CUBE_RE, _RES, MIRROR_TIMEOUT, RpeClient
from lib.rpe_gwt import build_flowsview_payload, extract_frame_ids, flowsview_header

logger = logging.getLogger(__name__)
TEMPLATES_PATH = Path(__file__).parent / "rpe_templates.json"


def fetch_fresh_cubeids(client: RpeClient) -> dict:
    """Tous les cubeIds rotatifs via un getFlowsView portant tous les frames du wallet."""
    client._gwt(_RES["gwt"]["getUserParams"])
    wallet = client._gwt(_RES["gwt"]["loadWallet"])
    header = flowsview_header(_RES["gwt"]["getFlowsView"][0])
    resp = client._gwt(build_flowsview_payload(extract_frame_ids(wallet), header))
    return {cube.split("_")[0]: cube for cube in _CUBE_RE.findall(resp)}


def assemble(current: dict, fresh_cubeids: dict) -> dict:
    """Candidat = catalogue/gwt/sel reportés + cubeName reporté + cubeId frais (ou absent si non trouvé)."""
    datasets = {}
    for key, ds in current["datasets"].items():
        entry = {"cubeName": ds["cubeName"]}
        if key in fresh_cubeids:
            entry["cubeId"] = fresh_cubeids[key]
        datasets[key] = entry
    return {"gwt": current["gwt"], "sel": current["sel"], "datasets": datasets, "catalog": current["catalog"]}


def gate(candidate: dict, smoke: dict) -> dict:
    """Verdict + couverture. smoke = {cube_key: nb_lignes renvoyées par une requête témoin}."""
    keys = list(candidate["datasets"])
    no_cubeid = [k for k in keys if not candidate["datasets"][k].get("cubeId")]
    no_rows = [k for k in keys if smoke.get(k, 0) == 0]
    passed = not no_cubeid and not no_rows
    return {
        "passed": passed,
        "failures": {"no_cubeid": no_cubeid, "no_rows": no_rows},
        "coverage": {
            "cubeids": "%d/%d" % (len(keys) - len(no_cubeid), len(keys)),
            "smoke": "%d/%d" % (len(keys) - len(no_rows), len(keys)),
        },
    }


def smoke_test(client: RpeClient, candidate: dict) -> dict:
    """Requête témoin par dataset (1re dimension du catalogue) → nb de lignes. Borne par MIRROR_TIMEOUT."""
    out = {}
    for key, ds in candidate["datasets"].items():
        cat = candidate["catalog"].get(key) or {}
        dims = cat.get("dimensions") or []
        if not ds.get("cubeId") or not dims:
            out[key] = 0
            continue
        client.cubeids[key] = ds["cubeId"]
        try:
            rows = client.query(ds["cubeName"], [dims[0]["id"]], timeout=MIRROR_TIMEOUT)
            out[key] = len(rows)
        except (
            httpx.HTTPError,
            KeyError,
        ) as e:  # Why: best-effort par dataset (comme mirror) — un dataset KO → 0 ligne → gate échoue
            logger.warning("smoke_test : échec %s : %s", ds["cubeName"], e)
            out[key] = 0
    return out


def build_templates(client: RpeClient | None = None, current: dict | None = None) -> tuple[dict, dict]:
    """Régénère le candidat browserless et renvoie (candidat, rapport)."""
    t0 = time.monotonic()
    own_client = client is None
    client = client or RpeClient.connect()
    current = current or json.loads(TEMPLATES_PATH.read_text(encoding="utf-8"))
    try:
        fresh = fetch_fresh_cubeids(client)
        candidate = assemble(current, fresh)
        smoke = smoke_test(client, candidate)
    finally:
        if own_client:
            client.close()
    report = gate(candidate, smoke)
    report["fully_browserless"] = True
    report["duration_s"] = round(time.monotonic() - t0, 1)
    logger.info(
        "build_templates : gate=%s cubeids=%s durée=%ss",
        report["passed"],
        report["coverage"]["cubeids"],
        report["duration_s"],
    )
    return candidate, report
