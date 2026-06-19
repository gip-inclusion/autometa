"""drop unused schema_version table

Revision ID: 7397f669848c
Revises: b12cbac64ff9
Create Date: 2026-06-19 14:53:34.648910

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "7397f669848c"
down_revision: Union[str, Sequence[str], None] = "b12cbac64ff9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.drop_table("schema_version")


def downgrade() -> None:
    """Downgrade schema."""
    op.create_table(
        "schema_version",
        sa.Column("version", sa.INTEGER(), autoincrement=True, nullable=False),
        sa.PrimaryKeyConstraint("version", name=op.f("schema_version_pkey")),
    )
