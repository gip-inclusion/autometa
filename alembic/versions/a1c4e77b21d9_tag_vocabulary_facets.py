"""Tag vocabulary: description, Notion sync keys, implications, sync state."""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "a1c4e77b21d9"
down_revision: Union[str, Sequence[str], None] = "f45e6ddef488"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("tags", sa.Column("description", sa.Text(), nullable=True))
    op.add_column("tags", sa.Column("notion_page_id", sa.Text(), nullable=True))
    op.add_column("tags", sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("true")))
    op.create_unique_constraint("uq_tags_notion_page_id", "tags", ["notion_page_id"])

    op.create_table(
        "tag_implications",
        sa.Column("tag_id", sa.Integer(), sa.ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("implies_tag_id", sa.Integer(), sa.ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True),
    )
    op.create_index("idx_tag_implications_tag", "tag_implications", ["tag_id"])

    op.create_table(
        "tag_sync_state",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_status", sa.Text(), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("term_count", sa.Integer(), nullable=False, server_default="0"),
    )


def downgrade() -> None:
    op.drop_table("tag_sync_state")
    op.drop_index("idx_tag_implications_tag", table_name="tag_implications")
    op.drop_table("tag_implications")
    op.drop_constraint("uq_tags_notion_page_id", "tags", type_="unique")
    op.drop_column("tags", "active")
    op.drop_column("tags", "notion_page_id")
    op.drop_column("tags", "description")
