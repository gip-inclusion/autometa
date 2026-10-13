"""Vérifie que la sauvegarde S3 du jour a bien produit son manifeste. Périodique."""

from web.backup_check import check_mirror_manifest
from web.cron_task import run

if __name__ == "__main__":
    run(check_mirror_manifest)
