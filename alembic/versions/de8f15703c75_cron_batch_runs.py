"""cron batch runs — un lot tué laisse un marqueur resté `running`."""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "de8f15703c75"
down_revision: Union[str, Sequence[str], None] = "5be6c06429dd"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "cron_batch_runs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("batch", sa.Text(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.add_column("cron_runs", sa.Column("batch_run_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "cron_runs_batch_run_id_fkey", "cron_runs", "cron_batch_runs", ["batch_run_id"], ["id"], ondelete="SET NULL"
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint("cron_runs_batch_run_id_fkey", "cron_runs", type_="foreignkey")
    op.drop_column("cron_runs", "batch_run_id")
    op.drop_table("cron_batch_runs")
