"""Run an agent's sub-agents on each production, in order, after the run and before delivery."""

import json

import httpx

from web import config

__all__ = ["run_chain"]

PYTHON_TYPES = {"string": str, "number": (int, float), "integer": int, "boolean": bool}


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
    # Why: a gateway or a proxy may answer 200 with an HTML page; that is a failing link, not a crash of the tick.
    try:
        return resp.json()
    except ValueError as exc:
        raise RuntimeError("réponse qui n'est pas du JSON") from exc


def chat(model: str, instructions: str, delivery: dict, **options) -> str:
    body = ollama(
        "api/chat",
        {
            "model": model,
            "stream": False,
            "messages": [
                {"role": "system", "content": instructions},
                {"role": "user", "content": f"# {delivery['title']}\n\n{delivery['text']}"},
            ],
            **options,
        },
    )
    try:
        return body["message"]["content"].strip()
    except (KeyError, TypeError, AttributeError) as exc:
        raise RuntimeError(f"réponse illisible : {type(exc).__name__}") from exc


def classify(subagent: dict, delivery: dict) -> tuple[dict, dict]:
    """A filter asks one yes/no question; a labeller asks one per label, in one call, and never sets aside."""
    labels = subagent.get("labels") or [{"name": "retenir", "question": subagent["question"]}]
    body = ollama(
        "v1/systemone",
        {
            "model": subagent["model"],
            "state": {"title": delivery["title"], "text": delivery["text"]},
            "questions": {e["name"]: {"type": "noul", "instructions": e["question"]} for e in labels},
        },
    )
    try:
        probabilities = {e["name"]: round(float(body["answers"][e["name"]]["noul"]), 4) for e in labels}
    except (KeyError, TypeError, ValueError) as exc:
        raise RuntimeError(f"réponse illisible : {type(exc).__name__}") from exc
    threshold = subagent["threshold"]
    if "question" in subagent:
        return delivery, {
            "probability": probabilities["retenir"],
            "threshold": threshold,
            "kept": probabilities["retenir"] >= threshold,
        }
    kept_labels = [name for name, p in probabilities.items() if p >= threshold]
    labels = [*delivery.get("labels", []), *(n for n in kept_labels if n not in delivery.get("labels", []))]
    text = f"{delivery['text']}\n\nÉtiquettes : {', '.join(kept_labels) or 'aucune'}"
    return {**delivery, "text": text, "labels": labels}, {
        "probabilities": probabilities,
        "threshold": threshold,
        "labels": kept_labels,
    }


def well_typed(value: object, kind: str) -> bool:
    """Why: a JSON true is a Python int too; only a boolean field takes a boolean."""
    return isinstance(value, PYTHON_TYPES[kind]) and isinstance(value, bool) == (kind == "boolean")


def extract(subagent: dict, delivery: dict) -> tuple[dict, dict]:
    schema = subagent["schema"]
    json_schema = {
        "type": "object",
        "properties": {k: {"type": t} for k, t in schema.items()},
        "required": list(schema),
        "additionalProperties": False,
    }
    instructions = "Extrais de ce texte les champs demandés. Réponds par l'objet JSON seul, sans rien inventer."
    raw = chat(subagent["model"], instructions, delivery, format=json_schema, options={"temperature": 0})
    try:
        fields = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError("extraction : sortie qui n'est pas du JSON") from exc
    if not (
        isinstance(fields, dict)
        and set(fields) == set(schema)
        and all(well_typed(fields[k], t) for k, t in schema.items())
    ):
        raise RuntimeError("extraction : sortie hors du schéma déclaré")
    lines = "\n".join(f"- {k} : {v}" for k, v in fields.items())
    return {**delivery, "text": f"{delivery['text']}\n\n{lines}"}, {"fields": fields}


def summarize(subagent: dict, delivery: dict) -> tuple[dict, dict]:
    limit = subagent["max_length"]
    instructions = (
        f"Résume ce texte en français, en {limit} caractères au plus. Garde les faits, n'ajoute ni lien, "
        "ni mention de personne, ni canal. Réponds par le résumé seul."
    )
    # Why: about 3 characters per token in French; the cap keeps a runaway answer bounded.
    text = chat(subagent["model"], instructions, delivery, options={"temperature": 0.2, "num_predict": limit // 2 + 64})
    if not text or len(text) > limit:
        raise RuntimeError(f"résumé de {len(text)} caractères, attendu 1 à {limit}")
    return {**delivery, "text": text}, {"length": len(text)}


STEPS = {"classifier": classify, "extraction": extract, "summary": summarize}


def run_chain(subagents: list[dict], delivery: dict) -> dict:
    """The production after each sub-agent in order: stops on a classifier below threshold or on a failing link."""
    steps = []
    for i, subagent in enumerate(subagents):
        try:
            delivery, step = STEPS[subagent["type"]](subagent, delivery)
        except (RuntimeError, httpx.HTTPError) as exc:
            failure = f"sous-agent {i + 1} ({subagent['type']} {subagent['model']}) en échec : {exc}"
            return {"delivery": delivery, "steps": steps, "calls": i + 1, "failure": failure}
        steps.append({"type": subagent["type"], "model": subagent["model"], **step})
        if step.get("kept") is False:
            break
    return {"delivery": delivery, "steps": steps, "calls": len(steps), "failure": None}
