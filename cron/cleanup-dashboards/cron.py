"""Signale les tableaux de bord orphelins, sans rien supprimer (dry-run). Périodique."""

from lib.dashboards import run_periodic_cleanup
from web.cron_task import run


def main() -> None:
    run_periodic_cleanup(dry_run=True)


if __name__ == "__main__":
    run(main)
