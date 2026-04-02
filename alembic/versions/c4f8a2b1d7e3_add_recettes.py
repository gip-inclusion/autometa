"""add recettes table.

Revision ID: c4f8a2b1d7e3
Revises: b3e7f1a2c4d9
Create Date: 2026-04-02
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "c4f8a2b1d7e3"
down_revision: Union[str, Sequence[str], None] = "b3e7f1a2c4d9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "recettes",
        sa.Column("id", sa.Text, primary_key=True),
        sa.Column("user_id", sa.Text),
        sa.Column("name", sa.Text, nullable=False),
        sa.Column("slug", sa.Text, nullable=False, unique=True),
        sa.Column("github_repo", sa.Text, nullable=False),
        sa.Column("status", sa.Text, nullable=False, server_default="cloned"),
        sa.Column("project_id", sa.Text, sa.ForeignKey("projects.id")),
        sa.Column("branch_a", sa.Text, nullable=False, server_default="main"),
        sa.Column("branch_b", sa.Text),
        sa.Column("port_a", sa.Integer),
        sa.Column("port_b", sa.Integer),
        sa.Column("deploy_url_a", sa.Text),
        sa.Column("deploy_url_b", sa.Text),
        sa.Column("pr_url", sa.Text),
        sa.Column("pr_status", sa.Text),
        sa.Column("created_at", sa.Text, nullable=False),
        sa.Column("updated_at", sa.Text, nullable=False),
    )
    op.create_index("idx_recettes_user", "recettes", ["user_id"])
    op.create_index("idx_recettes_slug", "recettes", ["slug"])


def downgrade() -> None:
    op.drop_table("recettes")
