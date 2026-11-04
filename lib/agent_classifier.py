"""Classify an agent's production with a model of the closed list, called by Autometa after the run."""

import httpx

from lib import agent_config
from web import config

__all__ = ["classify"]


def probability(modele: str, question: str, envoi: dict) -> float:
    """Probability that the answer to a yes/no question about the production is yes, from Ollama Cloud."""
    if not config.OLLAMA_API_KEY:
        raise RuntimeError("OLLAMA_API_KEY absent : le classificateur des agents n'est pas configuré")
    resp = httpx.post(
        f"{config.OLLAMA_REMOTE_BASE_URL.rstrip('/')}/v1/systemone",
        headers={"Authorization": f"Bearer {config.OLLAMA_API_KEY}"},
        json={
            "model": modele,
            "state": {"titre": envoi["titre"], "texte": envoi["texte"]},
            "questions": {"retenir": {"type": "noul", "instructions": question}},
        },
        timeout=config.OLLAMA_REQUEST_TIMEOUT,
    )
    resp.raise_for_status()
    try:
        return float(resp.json()["answers"]["retenir"]["noul"])
    except (KeyError, TypeError, ValueError) as exc:
        raise RuntimeError(f"réponse du classificateur illisible : {exc}") from exc


def classify(outils: list[dict], envoi: dict) -> list[dict]:
    """One verdict per tool of the agent: model id, probability of yes, threshold."""
    known = agent_config.modeles()
    return [
        {
            "modele": outil["id"],
            "probabilite": round(probability(known[outil["id"]]["modele"], outil["question"], envoi), 4),
            "seuil": outil["seuil"],
        }
        for outil in outils
    ]
