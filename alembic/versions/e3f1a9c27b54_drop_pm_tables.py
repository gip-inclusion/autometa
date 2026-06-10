"""drop unused pm_commands and pm_heartbeat tables (revision e3f1a9c27b54, revises df20b48b49c5)"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e3f1a9c27b54"
down_revision: Union[str, Sequence[str], None] = "df20b48b49c5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_index(op.f("idx_pm_commands_pending"), table_name="pm_commands")
    op.drop_table("pm_commands")
    op.drop_table("pm_heartbeat")


def downgrade() -> None:
    op.create_table(
        "pm_commands",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("conversation_id", sa.Text, nullable=False),
        sa.Column("command", sa.Text, nullable=False),
        sa.Column("payload", sa.Text),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("processed_at", sa.DateTime(timezone=True)),
    )
    op.create_index(
        "idx_pm_commands_pending", "pm_commands", ["processed_at"], postgresql_where=sa.text("processed_at IS NULL")
    )
    op.create_table(
        "pm_heartbeat",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("last_seen", sa.DateTime(timezone=True), nullable=False),
    )
