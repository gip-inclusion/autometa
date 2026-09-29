"""Mesure les tableaux de bord qui importent hors de la façade, et alerte sur changement. Périodique."""

from web.cron import discover_cron_tasks, report_facade_violations
from web.cron_task import run


def main() -> None:
    report_facade_violations(discover_cron_tasks(), notify=True)


if __name__ == "__main__":
    run(main)
