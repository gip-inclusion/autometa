"""add projects table, project_id to conversations.

Revision ID: b3e7f1a2c4d9
Revises: 0d4871663bfd
Create Date: 2026-04-01
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "b3e7f1a2c4d9"
down_revision: Union[str, Sequence[str], None] = "0d4871663bfd"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "projects",
        sa.Column("id", sa.Text, primary_key=True),
        sa.Column("user_id", sa.Text),
        sa.Column("name", sa.Text, nullable=False),
        sa.Column("slug", sa.Text, nullable=False, unique=True),
        sa.Column("description", sa.Text),
        sa.Column("spec", sa.Text),
        sa.Column("status", sa.Text, nullable=False, server_default="draft"),
        sa.Column("workflow_phase", sa.Text, nullable=False, server_default="planning"),
        sa.Column("created_at", sa.Text, nullable=False),
        sa.Column("updated_at", sa.Text, nullable=False),
    )
    op.create_index("idx_projects_user", "projects", ["user_id"])
    op.create_index("idx_projects_slug", "projects", ["slug"])

    op.add_column("conversations", sa.Column("project_id", sa.Text, sa.ForeignKey("projects.id")))
    op.create_index("idx_conversations_project", "conversations", ["project_id"])


def downgrade() -> None:
    op.drop_index("idx_conversations_project", table_name="conversations")
    op.drop_column("conversations", "project_id")
    op.drop_table("projects")
