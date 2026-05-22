import logging

from lib.dashboards import run_periodic_cleanup

logging.basicConfig(level=logging.INFO)
run_periodic_cleanup(dry_run=True)
