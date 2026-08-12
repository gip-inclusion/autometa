import logging
import time

from lib.tag_suggestions import run
from web.alerts import notify_alert_channel

logging.basicConfig(level=logging.INFO)

# Why: filet de rattrapage, pas un backfill. Le chemin normal est le taguage à la création
# (agent pour les TDB et rapports, thread Haiku pour les conversations) ; ce cron ne ramasse que
# ce qui est passé au travers — création sans tags, appel LLM en échec. Le rattrapage du corpus
# existant se fait par un run autometa-jobs (lib.tag_suggestions.export_for_job / ingest_job_output).
BUDGET_S = 600
BATCH = (("dashboard", 50), ("report", 50), ("conversation", 50))

started = time.monotonic()
summary = []
error = None

for object_type, batch_size in BATCH:
    left = BUDGET_S - (time.monotonic() - started)
    if left <= 0:
        break
    result = run(object_type=object_type, limit=batch_size, only_missing=True, time_budget_s=left)
    if result.get("error"):
        error = result["error"]
        break
    if result["processed"] or result["failed"] or result["deferred"]:
        summary.append(
            f"• {object_type} : {result['processed']} traité(s)"
            f"{', ' + str(result['failed']) + ' en échec' if result['failed'] else ''}"
            f"{', ' + str(result['deferred']) + ' reporté(s)' if result['deferred'] else ''}"
        )

if error:
    notify_alert_channel(f":warning: Rattrapage des suggestions de tags — {error}")
elif summary:
    notify_alert_channel("Rattrapage des suggestions de tags :\n" + "\n".join(summary))
