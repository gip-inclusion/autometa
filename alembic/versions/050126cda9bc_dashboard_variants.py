"""Déclinaisons d'un tableau de bord : clé, libellé et jeton, une ligne par déclinaison ; jetons obfusqués ou non."""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "050126cda9bc"
down_revision: Union[str, Sequence[str], None] = "fe7f423f6d57"
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
    )
    op.add_column(
        "dashboards",
        sa.Column("obfuscate_variants", sa.Boolean(), server_default=sa.text("false"), nullable=False),
    )


def downgrade() -> None:
    op.drop_column("dashboards", "obfuscate_variants")
    op.drop_table("dashboard_variants")
