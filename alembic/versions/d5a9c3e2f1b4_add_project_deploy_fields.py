"""add deploy fields to projects table.

Revision ID: d5a9c3e2f1b4
Revises: b3e7f1a2c4d9
Create Date: 2026-04-01
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "d5a9c3e2f1b4"
down_revision: Union[str, Sequence[str], None] = "b3e7f1a2c4d9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("projects", sa.Column("gitea_repo_id", sa.Integer))
    op.add_column("projects", sa.Column("gitea_url", sa.Text))
    op.add_column("projects", sa.Column("staging_branch", sa.Text, server_default="staging"))
    op.add_column("projects", sa.Column("production_branch", sa.Text, server_default="prod"))
    op.add_column("projects", sa.Column("staging_deploy_url", sa.Text))
    op.add_column("projects", sa.Column("production_deploy_url", sa.Text))
    op.add_column("projects", sa.Column("tech_stack", sa.Text))
    op.add_column("projects", sa.Column("boilerplate", sa.Text))


def downgrade() -> None:
    op.drop_column("projects", "boilerplate")
    op.drop_column("projects", "tech_stack")
    op.drop_column("projects", "production_deploy_url")
    op.drop_column("projects", "staging_deploy_url")
    op.drop_column("projects", "production_branch")
    op.drop_column("projects", "staging_branch")
    op.drop_column("projects", "gitea_url")
    op.drop_column("projects", "gitea_repo_id")
