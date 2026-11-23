"""Origine d'une conversation, au nom de qui son tour se joue, et pour celles venues de Slack leur fil et leur état."""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "5b7d2e9c41a6"
down_revision: Union[str, Sequence[str], None] = "3a555009668b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("conversations", sa.Column("origin", sa.Text(), server_default="web", nullable=False))
    op.add_column("conversations", sa.Column("slack_channel", sa.Text(), nullable=True))
    op.add_column("conversations", sa.Column("slack_thread_ts", sa.Text(), nullable=True))
    op.add_column("conversations", sa.Column("slack_message_ts", sa.Text(), nullable=True))
    op.add_column(
        "conversations", sa.Column("slack_locked", sa.Boolean(), server_default=sa.text("false"), nullable=False)
    )
    op.add_column("conversations", sa.Column("turn_user", sa.Text(), nullable=True))
    op.create_index(
        "idx_conversations_slack_thread",
        "conversations",
        ["slack_channel", "slack_thread_ts"],
        unique=True,
        postgresql_where=sa.text("slack_thread_ts IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("idx_conversations_slack_thread", table_name="conversations")
    op.drop_column("conversations", "turn_user")
    op.drop_column("conversations", "slack_locked")
    op.drop_column("conversations", "slack_message_ts")
    op.drop_column("conversations", "slack_thread_ts")
    op.drop_column("conversations", "slack_channel")
    op.drop_column("conversations", "origin")
