"""Run an agent's sub-agents on each production, in order, after the run and before delivery."""

import json

import httpx

from lib.agent_config import CHAMP_TYPES
from web import config

__all__ = ["run_chain"]

PYTHON_TYPES = {"texte": str, "nombre": (int, float), "entier": int, "booleen": bool}


def ollama(path: str, payload: dict) -> dict:
    """Why: Autometa's own key; the worker never holds one."""
    if not config.OLLAMA_API_KEY:
        raise RuntimeError("OLLAMA_API_KEY absent : les sous-agents des agents ne sont pas configurés")
    resp = httpx.post(
        f"{config.OLLAMA_REMOTE_BASE_URL.rstrip('/')}/{path}",
        headers={"Authorization": f"Bearer {config.OLLAMA_API_KEY}"},
        json=payload,
        timeout=config.OLLAMA_REQUEST_TIMEOUT,
    )
    resp.raise_for_status()
    return resp.json()


def chat(modele: str, consigne: str, envoi: dict, **options) -> str:
    body = ollama(
        "api/chat",
        {
            "model": modele,
            "stream": False,
            "messages": [
                {"role": "system", "content": consigne},
                {"role": "user", "content": f"# {envoi['titre']}\n\n{envoi['texte']}"},
            ],
            **options,
        },
    )
    try:
        return body["message"]["content"].strip()
    except (KeyError, TypeError, AttributeError) as exc:
        raise RuntimeError(f"réponse illisible : {type(exc).__name__}") from exc


def classify(outil: dict, envoi: dict) -> tuple[dict, dict]:
    body = ollama(
        "v1/systemone",
        {
            "model": outil["modele"],
            "state": {"titre": envoi["titre"], "texte": envoi["texte"]},
            "questions": {"retenir": {"type": "noul", "instructions": outil["question"]}},
        },
    )
    try:
        probabilite = round(float(body["answers"]["retenir"]["noul"]), 4)
    except (KeyError, TypeError, ValueError) as exc:
        raise RuntimeError(f"réponse illisible : {type(exc).__name__}") from exc
    return envoi, {"probabilite": probabilite, "seuil": outil["seuil"], "retenu": probabilite >= outil["seuil"]}


def well_typed(value: object, kind: str) -> bool:
    """Why: a JSON true is a Python int too; only a booleen field takes a boolean."""
    return isinstance(value, PYTHON_TYPES[kind]) and isinstance(value, bool) == (kind == "booleen")


def extract(outil: dict, envoi: dict) -> tuple[dict, dict]:
    schema = outil["schema"]
    json_schema = {
        "type": "object",
        "properties": {k: {"type": CHAMP_TYPES[t]} for k, t in schema.items()},
        "required": list(schema),
        "additionalProperties": False,
    }
    consigne = "Extrais de ce texte les champs demandés. Réponds par l'objet JSON seul, sans rien inventer."
    raw = chat(outil["modele"], consigne, envoi, format=json_schema, options={"temperature": 0})
    try:
        champs = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError("extraction : sortie qui n'est pas du JSON") from exc
    if not (
        isinstance(champs, dict)
        and set(champs) == set(schema)
        and all(well_typed(champs[k], t) for k, t in schema.items())
    ):
        raise RuntimeError("extraction : sortie hors du schéma déclaré")
    lignes = "\n".join(f"- {k} : {v}" for k, v in champs.items())
    return {**envoi, "texte": f"{envoi['texte']}\n\n{lignes}"}, {"champs": champs}


def summarize(outil: dict, envoi: dict) -> tuple[dict, dict]:
    limite = outil["longueur_max"]
    consigne = (
        f"Résume ce texte en français, en {limite} caractères au plus. Garde les faits, n'ajoute ni lien, "
        "ni mention de personne, ni canal. Réponds par le résumé seul."
    )
    # Why: about 3 characters per token in French; the cap keeps a runaway answer bounded.
    texte = chat(outil["modele"], consigne, envoi, options={"temperature": 0.2, "num_predict": limite // 2 + 64})
    if not texte or len(texte) > limite:
        raise RuntimeError(f"résumé de {len(texte)} caractères, attendu 1 à {limite}")
    return {**envoi, "texte": texte}, {"longueur": len(texte)}


STEPS = {"classificateur": classify, "extraction": extract, "resume": summarize}


def run_chain(outils: list[dict], envoi: dict) -> dict:
    """The production after each sub-agent in order: stops on a classifier below threshold or on a failing link."""
    etapes = []
    for i, outil in enumerate(outils):
        try:
            envoi, etape = STEPS[outil["type"]](outil, envoi)
        except (RuntimeError, httpx.HTTPError) as exc:
            echec = f"sous-agent {i + 1} ({outil['type']} {outil['modele']}) en échec : {exc}"
            return {"envoi": envoi, "etapes": etapes, "appels": i + 1, "echec": echec}
        etapes.append({"type": outil["type"], "modele": outil["modele"], **etape})
        if etape.get("retenu") is False:
            break
    return {"envoi": envoi, "etapes": etapes, "appels": len(etapes), "echec": None}
