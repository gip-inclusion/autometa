import logging
import time

from lib.tag_suggestions import run
from web.alerts import notify_alert_channel

logging.basicConfig(level=logging.INFO)

# Why: 1500s sous le timeout de 1800s — la marge laisse la derniere ecriture se terminer.
BUDGET_S = 1500

# Why: par ordre de valeur, avec un plafond par passe. Chaque passe ignore les objets déjà
# suggérés : le corpus est parcouru par tranches d'une nuit sur l'autre au lieu de dépasser le
# timeout d'un coup. Le plafond borne aussi la collecte elle-même, qui précède la boucle budgétée.
BATCH = (("dashboard", 200), ("report", 200), ("conversation", 300))

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
    notify_alert_channel(f":warning: Suggestions de tags — {error}")
elif summary:
    notify_alert_channel("Suggestions de tags :\n" + "\n".join(summary))
