import logging

from lib.tag_sync import pending_terms, sync_tags
from web import config
from web.alerts import notify_alert_channel

logging.basicConfig(level=logging.INFO)

result = sync_tags()

if result.error:
    notify_alert_channel(f":warning: Synchro tags Notion refusée — {result.error}")
elif result.rejected:
    lines = "\n".join(f"• {reason}" for reason in result.rejected)
    notify_alert_channel(f":warning: Synchro tags Notion — {len(result.rejected)} ligne(s) rejetée(s) :\n{lines}")

# Why: la promotion se fait dans Notion — le seul manque était de savoir qu'il y a quelque chose à relire.
pending = pending_terms()
if pending:
    lines = "\n".join(f"• `{t['name']}` ({t['facet']}) — {t['usages']} usage(s)" for t in pending)
    link = f"\n<{config.NOTION_TAGS_DB}|Ouvrir la base des tags>" if config.NOTION_TAGS_DB else ""
    notify_alert_channel(f":label: {len(pending)} terme(s) proposé(s) à valider :\n{lines}{link}")
