"""publication_refresh_columns (Revises 401dce8c4864)"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "7b7df556b6d0"
down_revision: Union[str, Sequence[str], None] = "401dce8c4864"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "dashboard_publications",
        sa.Column("snapshot_has_cron", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.alter_column("dashboard_publications", "snapshot_has_cron", server_default=None)
    op.add_column(
        "dashboard_publications",
        sa.Column("refresh_paused_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "dashboard_publications",
        sa.Column("last_successful_refresh_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "dashboard_publications",
        sa.Column("last_refresh_status", sa.Text(), nullable=True),
    )
    op.add_column(
        "dashboard_publications",
        sa.Column("last_refresh_error", sa.Text(), nullable=True),
    )
    op.create_index(
        "idx_dashboard_publications_refreshable",
        "dashboard_publications",
        ["snapshot_has_cron", "unpublished_at", "refresh_paused_at"],
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("idx_dashboard_publications_refreshable", table_name="dashboard_publications")
    op.drop_column("dashboard_publications", "last_refresh_error")
    op.drop_column("dashboard_publications", "last_refresh_status")
    op.drop_column("dashboard_publications", "last_successful_refresh_at")
    op.drop_column("dashboard_publications", "refresh_paused_at")
    op.drop_column("dashboard_publications", "snapshot_has_cron")
