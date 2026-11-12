"""Livre les runs terminés des agents, puis lance ceux dont la cadence tombe. Périodique."""

from lib.agents import tick
from web.cron_task import run

if __name__ == "__main__":
    run(tick)
