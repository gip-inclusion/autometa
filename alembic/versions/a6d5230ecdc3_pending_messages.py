"""Messages écrits pendant un tour, en attente de sa fin, portés par conversations.pending_messages."""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "a6d5230ecdc3"
down_revision: Union[str, Sequence[str], None] = "046795c5db73"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "conversations", sa.Column("pending_messages", postgresql.JSONB(astext_type=sa.Text()), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("conversations", "pending_messages")
