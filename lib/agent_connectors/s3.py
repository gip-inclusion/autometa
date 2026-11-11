"""Preparation s3: a dataset published by publish_dataset, handed to the run as a presigned URL."""

import re

from lib import job_inputs
from web import s3

DESCRIPTION = "un jeu de données publié par publish_dataset ; le run reçoit son URL à télécharger"
FIELDS = {"dataset": "obligatoire, le fichier publié, par exemple services.sqlite"}


def errors(step: dict) -> list[str]:
    if not (
        isinstance(step.get("dataset"), str)
        and re.fullmatch(r"[a-z0-9][a-z0-9_-]*\.(sqlite|jsonl|csv)", step["dataset"])
    ):
        return ["dataset : attendu un fichier publié par publish_dataset, par exemple services.sqlite."]
    return []


def source(step: dict) -> str:
    return step["dataset"]


def prepare(step: dict, cap: int, cursor: int) -> dict:
    url = s3.job_inputs.get_url(step["dataset"], expires_in=job_inputs.DEFAULT_EXPIRES)
    if not (url and s3.job_inputs.exists(step["dataset"])):
        raise ValueError(f"préparation s3 {step['dataset']} : jeu introuvable, le run n'est pas lancé")
    return {"content": url}
