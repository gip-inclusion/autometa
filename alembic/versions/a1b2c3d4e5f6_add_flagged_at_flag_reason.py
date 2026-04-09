"""add flagged_at and flag_reason to conversations.

Revision ID: a1b2c3d4e5f6
Revises: 0d4871663bfd
Create Date: 2026-04-02
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, Sequence[str], None] = "0d4871663bfd"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("conversations", sa.Column("flagged_at", sa.Text(), nullable=True))
    op.add_column("conversations", sa.Column("flag_reason", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("conversations", "flag_reason")
    op.drop_column("conversations", "flagged_at")
