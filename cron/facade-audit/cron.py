"""Mesure les tableaux de bord qui importent hors de la façade, alerte sur changement, publie l'inventaire. Périodique."""

from web.cron import discover_cron_tasks, report_facade_violations
from web.cron_task import run
from web.facade_manifest import build_manifest, publish_manifest


def main() -> None:
    tasks = discover_cron_tasks()
    report_facade_violations(tasks, notify=True)
    publish_manifest(build_manifest(tasks))


if __name__ == "__main__":
    run(main)
