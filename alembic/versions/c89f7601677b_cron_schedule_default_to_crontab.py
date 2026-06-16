"""cron_schedule default to crontab

Revision ID: c89f7601677b
Revises: 1ab3818607f7
Create Date: 2026-06-07 16:23:06.544358

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c89f7601677b"
down_revision: Union[str, Sequence[str], None] = "1ab3818607f7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column("dashboards", "cron_schedule", server_default="0 6 * * *")
    op.execute(sa.text("UPDATE dashboards SET cron_schedule = '0 6 * * *' WHERE cron_schedule = 'daily'"))
    op.execute(sa.text("UPDATE dashboards SET cron_schedule = '0 6 * * 1' WHERE cron_schedule = 'weekly'"))
    op.execute(sa.text("UPDATE dashboards SET cron_schedule = '0 6 1 * *' WHERE cron_schedule = 'monthly'"))


def downgrade() -> None:
    op.alter_column("dashboards", "cron_schedule", server_default="daily")
