"""Rattrape les objets restés sans suggestion de tags, par petits lots et sur un budget de temps."""

import logging
import time

from lib.tag_suggestions import run
from web.alerts import notify_alert_channel

# Why: filet de rattrapage, pas un backfill. Le chemin normal est le taguage à la création
# (agent pour les TDB et rapports, thread Haiku pour les conversations) ; ce cron ne ramasse que
# ce qui est passé au travers — création sans tags, appel LLM en échec. Le rattrapage du corpus
# existant se fait par un run autometa-jobs (lib.tag_suggestions.export_for_job / ingest_job_output).
BUDGET_S = 600
BATCH = (("dashboard", 50), ("report", 50), ("conversation", 50))


def main() -> None:
    started = time.monotonic()
    summary = []
    error = None
    outage = False

    for object_type, batch_size in BATCH:
        left = BUDGET_S - (time.monotonic() - started)
        if left <= 0:
            break
        result = run(object_type=object_type, limit=batch_size, only_missing=True, time_budget_s=left)
        if result.get("error"):
            error = result["error"]
            break
        # Why: un lot où tout échoue signale un CLI cassé, pas des sujets difficiles — sans le
        # drapeau, le message Slack serait indistinguable d'un run sain.
        outage |= bool(result["failed"] and not result["processed"])
        if result["processed"] or result["failed"] or result["deferred"]:
            summary.append(
                f"• {object_type} : {result['processed']} traité(s)"
                f"{', ' + str(result['failed']) + ' en échec' if result['failed'] else ''}"
                f"{', ' + str(result['deferred']) + ' reporté(s)' if result['deferred'] else ''}"
            )

    if error:
        notify_alert_channel(f":warning: Rattrapage des suggestions de tags — {error}")
    elif summary:
        prefix = ":warning: " if outage else ""
        notify_alert_channel(f"{prefix}Rattrapage des suggestions de tags :\n" + "\n".join(summary))


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
