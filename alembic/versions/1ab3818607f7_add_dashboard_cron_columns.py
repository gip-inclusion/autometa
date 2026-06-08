"""add dashboard cron columns

Revision ID: 1ab3818607f7
Revises: 7b7df556b6d0
Create Date: 2026-06-05 20:41:15.361973

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "1ab3818607f7"
down_revision: Union[str, Sequence[str], None] = "7b7df556b6d0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("dashboards", sa.Column("cron_schedule", sa.Text(), server_default="daily", nullable=False))
    op.add_column("dashboards", sa.Column("cron_timeout", sa.Integer(), server_default="300", nullable=False))
    op.add_column("dashboards", sa.Column("cron_enabled", sa.Boolean(), server_default=sa.text("true"), nullable=False))


def downgrade() -> None:
    op.drop_column("dashboards", "cron_enabled")
    op.drop_column("dashboards", "cron_timeout")
    op.drop_column("dashboards", "cron_schedule")
