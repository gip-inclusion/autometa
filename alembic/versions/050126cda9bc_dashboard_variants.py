"""Déclinaisons d'un tableau de bord : clé, libellé et jeton, une ligne par déclinaison."""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "050126cda9bc"
down_revision: Union[str, Sequence[str], None] = "c7a2e9b4d1f0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "dashboard_variants",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("dashboard_slug", sa.Text(), nullable=False),
        sa.Column("key", sa.Text(), nullable=False),
        sa.Column("label", sa.Text(), nullable=False),
        sa.Column("token", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["dashboard_slug"], ["dashboards.slug"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("dashboard_slug", "key", name="uq_dashboard_variants_slug_key"),
        sa.UniqueConstraint("token", name="uq_dashboard_variants_token"),
    )


def downgrade() -> None:
    op.drop_table("dashboard_variants")
