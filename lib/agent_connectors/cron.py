"""Preparation cron: the last successful output of a task of cron/, never run again for the agent."""

import difflib

from web import config, cron

DESCRIPTION = "la dernière sortie réussie d'une tâche de cron/, jamais relancée"
CHAMPS = {"tache": "obligatoire, une tâche de cron/ (liste rendue par destinations)"}
# Why: the agents' own generic cron feeds no agent.
GENERIC_CRON = "run-agents"


def tasks() -> list[str]:
    return sorted(d.name for d in config.CRON_DIR.iterdir() if (d / "cron.py").is_file() and d.name != GENERIC_CRON)


def errors(step: dict) -> list[str]:
    if step.get("tache") not in (known := tasks()):
        close = difflib.get_close_matches(str(step.get("tache")), known, n=1, cutoff=0.6)
        hint = f" Vouliez-vous dire {close[0]!r} ?" if close else ""
        return [f"tache : {step.get('tache')!r} n'est pas une tâche de cron/.{hint}"]
    return []


def source(step: dict) -> str:
    return step["tache"]


def prepare(step: dict, plafond: int, debut: int) -> dict:
    runs = cron.get_app_runs(step["tache"], limit=1)
    if not runs or runs[0]["status"] != "success":
        raise ValueError(f"préparation cron {step['tache']} : pas de dernière sortie réussie, le run n'est pas lancé")
    return {"contenu": runs[0]["output"]}
