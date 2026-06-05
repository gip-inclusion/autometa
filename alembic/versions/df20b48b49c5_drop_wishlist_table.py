"""drop wishlist table (revision df20b48b49c5, revises 7b7df556b6d0)"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "df20b48b49c5"
down_revision: Union[str, Sequence[str], None] = "7b7df556b6d0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_index(op.f("idx_wishlist_category"), table_name="wishlist")
    op.drop_index(op.f("idx_wishlist_status"), table_name="wishlist")
    op.drop_table("wishlist")


def downgrade() -> None:
    op.create_table(
        "wishlist",
        sa.Column("id", sa.INTEGER(), autoincrement=True, nullable=False),
        sa.Column("timestamp", postgresql.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("category", sa.TEXT(), nullable=False),
        sa.Column("title", sa.TEXT(), nullable=False),
        sa.Column("description", sa.TEXT(), nullable=True),
        sa.Column("conversation_id", sa.TEXT(), nullable=True),
        sa.Column("status", sa.TEXT(), server_default=sa.text("'open'::text"), nullable=False),
        sa.Column("notion_page_id", sa.TEXT(), nullable=True),
        sa.PrimaryKeyConstraint("id", name=op.f("wishlist_pkey")),
    )
    op.create_index(op.f("idx_wishlist_status"), "wishlist", ["status"], unique=False)
    op.create_index(op.f("idx_wishlist_category"), "wishlist", ["category"], unique=False)
