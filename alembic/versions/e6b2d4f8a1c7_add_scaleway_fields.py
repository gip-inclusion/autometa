"""add scaleway fields to projects table.

Revision ID: e6b2d4f8a1c7
Revises: d5a9c3e2f1b4
Create Date: 2026-04-01
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "e6b2d4f8a1c7"
down_revision: Union[str, Sequence[str], None] = "d5a9c3e2f1b4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("projects", sa.Column("scaleway_container_id", sa.Text))
    op.add_column("projects", sa.Column("scaleway_url", sa.Text))
    op.add_column("projects", sa.Column("scaleway_db_url", sa.Text))


def downgrade() -> None:
    op.drop_column("projects", "scaleway_db_url")
    op.drop_column("projects", "scaleway_url")
    op.drop_column("projects", "scaleway_container_id")
