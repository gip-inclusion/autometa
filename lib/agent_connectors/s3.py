"""Preparation s3: a dataset published by publish_dataset, handed to the run as a presigned URL."""

import re

from lib import job_inputs
from web import s3

DESCRIPTION = "un jeu de données publié par publish_dataset ; le run reçoit son URL à télécharger"
CHAMPS = {"jeu": "obligatoire, le fichier publié, par exemple services.sqlite"}


def errors(step: dict) -> list[str]:
    if not (isinstance(step.get("jeu"), str) and re.fullmatch(r"[a-z0-9][a-z0-9_-]*\.(sqlite|jsonl|csv)", step["jeu"])):
        return ["jeu : attendu un fichier publié par publish_dataset, par exemple services.sqlite."]
    return []


def source(step: dict) -> str:
    return step["jeu"]


def prepare(step: dict, plafond: int, debut: int) -> dict:
    url = s3.job_inputs.get_url(step["jeu"], expires_in=job_inputs.DEFAULT_EXPIRES)
    if not (url and s3.job_inputs.exists(step["jeu"])):
        raise ValueError(f"préparation s3 {step['jeu']} : jeu introuvable, le run n'est pas lancé")
    return {"contenu": url}
