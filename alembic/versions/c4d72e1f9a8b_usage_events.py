"""usage_events table"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "c4d72e1f9a8b"
down_revision: Union[str, Sequence[str], None] = "7946c9c555a4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "usage_events",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("conversation_id", sa.Text(), nullable=True),
        sa.Column("cli_message_id", sa.Text(), nullable=True),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("kind", sa.Text(), nullable=False, server_default="turn"),
        sa.Column("model", sa.Text(), nullable=True),
        sa.Column("backend", sa.Text(), nullable=False),
        sa.Column("service_tier", sa.Text(), nullable=True),
        sa.Column("input_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("output_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("cache_creation_5m_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("cache_creation_1h_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("cache_read_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("web_search_requests", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("web_fetch_requests", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("raw", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.ForeignKeyConstraint(["conversation_id"], ["conversations.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_usage_events_conv_ts", "usage_events", ["conversation_id", "timestamp"], unique=False)
    op.create_index("idx_usage_events_ts", "usage_events", ["timestamp"], unique=False)
    op.create_index("idx_usage_events_kind_ts", "usage_events", ["kind", "timestamp"], unique=False)


def downgrade() -> None:
    op.drop_index("idx_usage_events_kind_ts", table_name="usage_events")
    op.drop_index("idx_usage_events_ts", table_name="usage_events")
    op.drop_index("idx_usage_events_conv_ts", table_name="usage_events")
    op.drop_table("usage_events")
