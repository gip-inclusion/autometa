"""Preparation cron: the last successful output of a task of cron/, never run again for the agent."""

import difflib

from web import config, cron

DESCRIPTION = "la dernière sortie réussie d'une tâche de cron/, jamais relancée"
FIELDS = {"task": "obligatoire, une tâche de cron/ (liste rendue par destinations)"}
# Why: the agents' own generic cron feeds no agent.
GENERIC_CRON = "run-agents"


def tasks() -> list[str]:
    return sorted(d.name for d in config.CRON_DIR.iterdir() if (d / "cron.py").is_file() and d.name != GENERIC_CRON)


def errors(step: dict) -> list[str]:
    if step.get("task") not in (known := tasks()):
        close = difflib.get_close_matches(str(step.get("task")), known, n=1, cutoff=0.6)
        hint = f" Vouliez-vous dire {close[0]!r} ?" if close else ""
        return [f"task : {step.get('task')!r} n'est pas une tâche de cron/.{hint}"]
    return []


def source(step: dict) -> str:
    return step["task"]


def prepare(step: dict, cap: int, cursor: int) -> dict:
    runs = cron.get_app_runs(step["task"], limit=1)
    if not runs or runs[0]["status"] != "success":
        raise ValueError(f"préparation cron {step['task']} : pas de dernière sortie réussie, le run n'est pas lancé")
    return {"content": runs[0]["output"]}
