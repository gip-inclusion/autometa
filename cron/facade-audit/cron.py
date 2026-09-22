import logging

from web.cron import discover_cron_tasks, report_facade_violations

logging.basicConfig(level=logging.INFO)

report_facade_violations(discover_cron_tasks(), notify=True)
