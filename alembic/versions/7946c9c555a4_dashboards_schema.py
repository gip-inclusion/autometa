"""dashboards schema

Revision ID: 7946c9c555a4
Revises: 5759bd430b2e
Create Date: 2026-05-08 12:30:57.839555

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "7946c9c555a4"
down_revision: Union[str, Sequence[str], None] = "5759bd430b2e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "dashboards",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("slug", sa.Text(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("website", sa.Text(), nullable=True),
        sa.Column("category", sa.Text(), nullable=True),
        sa.Column("first_author_email", sa.Text(), nullable=False),
        sa.Column("created_in_conversation_id", sa.Text(), nullable=True),
        sa.Column("is_archived", sa.Boolean(), nullable=False),
        sa.Column("has_api_access", sa.Boolean(), nullable=False),
        sa.Column("has_cron", sa.Boolean(), nullable=False),
        sa.Column("has_persistence", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug"),
    )
    op.create_table(
        "dashboard_tags",
        sa.Column("dashboard_slug", sa.Text(), nullable=False),
        sa.Column("tag_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["dashboard_slug"], ["dashboards.slug"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tag_id"], ["tags.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("dashboard_slug", "tag_id"),
    )
    op.create_index("idx_dashboard_tags_slug", "dashboard_tags", ["dashboard_slug"], unique=False)
    op.create_index("idx_dashboard_tags_tag", "dashboard_tags", ["tag_id"], unique=False)


def downgrade() -> None:
    op.drop_index("idx_dashboard_tags_tag", table_name="dashboard_tags")
    op.drop_index("idx_dashboard_tags_slug", table_name="dashboard_tags")
    op.drop_table("dashboard_tags")
    op.drop_table("dashboards")
