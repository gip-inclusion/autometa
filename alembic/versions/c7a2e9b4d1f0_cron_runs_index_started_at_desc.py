"""Rétablit le DESC sur started_at dans idx_cron_runs_slug_started, perdu par a1b2c3d4e5f6."""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "c7a2e9b4d1f0"
down_revision: Union[str, Sequence[str], None] = "385f7fb3f2f8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_index("idx_cron_runs_slug_started", table_name="cron_runs")
    op.create_index("idx_cron_runs_slug_started", "cron_runs", ["app_slug", sa.text("started_at DESC")])


def downgrade() -> None:
    op.drop_index("idx_cron_runs_slug_started", table_name="cron_runs")
    op.create_index("idx_cron_runs_slug_started", "cron_runs", ["app_slug", "started_at"])
