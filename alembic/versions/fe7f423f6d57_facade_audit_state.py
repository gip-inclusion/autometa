"""facade audit state — l'état de l'audit de façade quitte dashboard_storage pour le schéma applicatif."""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "fe7f423f6d57"
down_revision: Union[str, Sequence[str], None] = "de8f15703c75"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "facade_audit_state",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("slugs", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("reported_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("facade_audit_state")
