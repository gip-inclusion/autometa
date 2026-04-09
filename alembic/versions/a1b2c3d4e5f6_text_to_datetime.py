"""Convert datetime text columns to native timestamptz."""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, Sequence[str], None] = "0d4871663bfd"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# (table, column, nullable)
COLUMNS = [
    ("conversations", "created_at", False),
    ("conversations", "updated_at", False),
    ("conversations", "pinned_at", True),
    ("messages", "timestamp", False),
    ("reports", "created_at", False),
    ("reports", "updated_at", False),
    ("uploaded_files", "created_at", False),
    ("cron_runs", "started_at", False),
    ("cron_runs", "finished_at", True),
    ("pinned_items", "pinned_at", False),
    ("pm_commands", "created_at", False),
    ("pm_commands", "processed_at", True),
    ("pm_heartbeat", "last_seen", False),
]

OLD_INDEXES = [
    "idx_conversations_updated",
    "idx_conversations_user_updated",
    "idx_reports_updated",
    "idx_cron_runs_slug_started",
]


def to_timestamptz(table, column, nullable):
    tmp = "_" + column + "_ts"
    op.add_column(table, sa.Column(tmp, sa.DateTime(timezone=True)))
    conn = op.get_bind()
    # Why: table/column are hardcoded constants above, not user input.
    conn.execute(sa.text(
        'UPDATE "' + table + '" SET "' + tmp + '" = "' + column + '"::timestamptz'
        + ' WHERE "' + column + '" IS NOT NULL'
    ))
    op.drop_column(table, column)
    op.alter_column(table, tmp, new_column_name=column, nullable=nullable)


def to_text(table, column, nullable):
    tmp = "_" + column + "_txt"
    op.add_column(table, sa.Column(tmp, sa.Text))
    conn = op.get_bind()
    # Why: table/column are hardcoded constants above, not user input.
    conn.execute(sa.text(
        'UPDATE "' + table + '" SET "' + tmp + '"'
        " = to_char(\"" + column + "\", 'YYYY-MM-DD\"T\"HH24:MI:SS.US+00:00')"
        ' WHERE "' + column + '" IS NOT NULL'
    ))
    op.drop_column(table, column)
    op.alter_column(table, tmp, new_column_name=column, nullable=nullable)


def upgrade() -> None:
    for table, column, nullable in COLUMNS:
        to_timestamptz(table, column, nullable)

    for idx_name in OLD_INDEXES:
        op.execute(sa.text('DROP INDEX IF EXISTS "' + idx_name + '"'))

    op.create_index("idx_conversations_updated", "conversations", ["updated_at"])
    op.create_index("idx_conversations_user_updated", "conversations", ["user_id", "updated_at"])
    op.create_index("idx_reports_updated", "reports", ["updated_at"])
    op.create_index("idx_cron_runs_slug_started", "cron_runs", ["app_slug", "started_at"])


def downgrade() -> None:
    for table, column, nullable in COLUMNS:
        to_text(table, column, nullable)

    for idx_name in OLD_INDEXES:
        op.execute(sa.text('DROP INDEX IF EXISTS "' + idx_name + '"'))

    op.create_index("idx_conversations_updated", "conversations", ["updated_at"],
                     postgresql_ops={"updated_at": "DESC"})
    op.create_index("idx_conversations_user_updated", "conversations", ["user_id", "updated_at"],
                     postgresql_ops={"updated_at": "DESC"})
    op.create_index("idx_reports_updated", "reports", ["updated_at"],
                     postgresql_ops={"updated_at": "DESC"})
    op.create_index("idx_cron_runs_slug_started", "cron_runs", ["app_slug", "started_at"],
                     postgresql_ops={"started_at": "DESC"})
