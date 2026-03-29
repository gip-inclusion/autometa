"""initial schema — all 21 tables.

Production databases are already at this state; run `alembic stamp head` to skip.

Revision ID: 0d4871663bfd
Revises:
Create Date: 2026-03-29
"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0d4871663bfd"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TABLES = [
    "conversations",
    "messages",
    "reports",
    "tags",
    "conversation_tags",
    "report_tags",
    "uploaded_files",
    "cron_runs",
    "pinned_items",
    "pm_commands",
    "pm_heartbeat",
    "wishlist",
    "schema_version",
    "matomo_baselines",
    "matomo_dimensions",
    "matomo_segments",
    "matomo_events",
    "metabase_cards",
    "metabase_dashboards",
]


def upgrade() -> None:
    op.create_table(
        "conversations",
        sa.Column("id", sa.Text, primary_key=True),
        sa.Column("user_id", sa.Text),
        sa.Column("title", sa.Text),
        sa.Column("session_id", sa.Text),
        sa.Column("conv_type", sa.Text, nullable=False, server_default="exploration"),
        sa.Column("file_path", sa.Text),
        sa.Column("status", sa.Text, nullable=False, server_default="active"),
        sa.Column("pr_url", sa.Text),
        sa.Column("forked_from", sa.Text),
        sa.Column("usage_input_tokens", sa.Integer, nullable=False, server_default="0"),
        sa.Column("usage_output_tokens", sa.Integer, nullable=False, server_default="0"),
        sa.Column("usage_cache_creation_tokens", sa.Integer, nullable=False, server_default="0"),
        sa.Column("usage_cache_read_tokens", sa.Integer, nullable=False, server_default="0"),
        sa.Column("usage_backend", sa.Text),
        sa.Column("usage_extra", sa.Text),
        sa.Column("pinned_at", sa.Text),
        sa.Column("pinned_label", sa.Text),
        sa.Column("needs_response", sa.Integer, nullable=False, server_default="0"),
        sa.Column("created_at", sa.Text, nullable=False),
        sa.Column("updated_at", sa.Text, nullable=False),
    )
    op.create_index("idx_conversations_updated", "conversations", [sa.text("updated_at DESC")])
    op.create_index("idx_conversations_type_status", "conversations", ["conv_type", "status"])
    op.create_index("idx_conversations_user_updated", "conversations", ["user_id", sa.text("updated_at DESC")])
    op.create_index(
        "idx_conversations_needs_response",
        "conversations",
        ["needs_response"],
        postgresql_where=sa.text("needs_response = 1"),
    )

    op.create_table(
        "messages",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("conversation_id", sa.Text, sa.ForeignKey("conversations.id"), nullable=False),
        sa.Column("type", sa.Text),
        sa.Column("role", sa.Text, nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("raw_events", sa.Text),
        sa.Column("timestamp", sa.Text, nullable=False),
    )
    op.create_index("idx_messages_conversation", "messages", ["conversation_id"])
    op.create_index("idx_messages_conv_id", "messages", ["conversation_id", "id"])

    op.create_table(
        "reports",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("title", sa.Text, nullable=False),
        sa.Column("content", sa.Text),
        sa.Column("website", sa.Text),
        sa.Column("category", sa.Text),
        sa.Column("tags", sa.Text),
        sa.Column("original_query", sa.Text),
        sa.Column("source_conversation_id", sa.Text),
        sa.Column("user_id", sa.Text),
        sa.Column("version", sa.Integer, server_default="1"),
        sa.Column("archived", sa.Integer, server_default="0"),
        sa.Column("notion_url", sa.Text),
        sa.Column("created_at", sa.Text, nullable=False),
        sa.Column("updated_at", sa.Text, nullable=False),
        sa.Column("conversation_id", sa.Text),
        sa.Column("message_id", sa.Integer),
    )
    op.create_index("idx_reports_updated", "reports", [sa.text("updated_at DESC")])

    op.create_table(
        "tags",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("name", sa.Text, nullable=False, unique=True),
        sa.Column("type", sa.Text, nullable=False),
        sa.Column("label", sa.Text, nullable=False),
    )
    op.create_index("idx_tags_type", "tags", ["type"])

    op.create_table(
        "conversation_tags",
        sa.Column("conversation_id", sa.Text, sa.ForeignKey("conversations.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("tag_id", sa.Integer, sa.ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True),
    )
    op.create_index("idx_conversation_tags_conv", "conversation_tags", ["conversation_id"])
    op.create_index("idx_conversation_tags_tag", "conversation_tags", ["tag_id"])

    op.create_table(
        "report_tags",
        sa.Column("report_id", sa.Integer, sa.ForeignKey("reports.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("tag_id", sa.Integer, sa.ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True),
    )
    op.create_index("idx_report_tags_report", "report_tags", ["report_id"])
    op.create_index("idx_report_tags_tag", "report_tags", ["tag_id"])

    op.create_table(
        "uploaded_files",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("conversation_id", sa.Text, sa.ForeignKey("conversations.id", ondelete="CASCADE")),
        sa.Column("user_id", sa.Text),
        sa.Column("original_filename", sa.Text, nullable=False),
        sa.Column("stored_filename", sa.Text, nullable=False),
        sa.Column("storage_path", sa.Text, nullable=False),
        sa.Column("file_size", sa.Integer, nullable=False),
        sa.Column("mime_type", sa.Text),
        sa.Column("sha256_hash", sa.Text, nullable=False),
        sa.Column("is_text", sa.Boolean, server_default="false"),
        sa.Column("av_scanned", sa.Boolean, server_default="false"),
        sa.Column("av_clean", sa.Boolean),
        sa.Column("created_at", sa.Text, nullable=False),
    )
    op.create_index("idx_uploaded_files_conversation", "uploaded_files", ["conversation_id"])
    op.create_index("idx_uploaded_files_hash", "uploaded_files", ["sha256_hash"])
    op.create_index("idx_uploaded_files_user", "uploaded_files", ["user_id"])

    op.create_table(
        "cron_runs",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("app_slug", sa.Text, nullable=False),
        sa.Column("started_at", sa.Text, nullable=False),
        sa.Column("finished_at", sa.Text),
        sa.Column("status", sa.Text, nullable=False),
        sa.Column("output", sa.Text),
        sa.Column("duration_ms", sa.Integer),
        sa.Column("trigger", sa.Text, nullable=False, server_default="scheduled"),
    )
    op.create_index("idx_cron_runs_slug_started", "cron_runs", ["app_slug", sa.text("started_at DESC")])

    op.create_table(
        "pinned_items",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("item_type", sa.Text, nullable=False),
        sa.Column("item_id", sa.Text, nullable=False),
        sa.Column("label", sa.Text),
        sa.Column("pinned_at", sa.Text, nullable=False),
        sa.UniqueConstraint("item_type", "item_id"),
    )

    op.create_table(
        "pm_commands",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("conversation_id", sa.Text, nullable=False),
        sa.Column("command", sa.Text, nullable=False),
        sa.Column("payload", sa.Text),
        sa.Column("created_at", sa.Text, nullable=False),
        sa.Column("processed_at", sa.Text),
    )
    op.create_index(
        "idx_pm_commands_pending", "pm_commands", ["processed_at"], postgresql_where=sa.text("processed_at IS NULL")
    )

    op.create_table(
        "pm_heartbeat",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("last_seen", sa.Text, nullable=False),
    )

    op.create_table(
        "wishlist",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("timestamp", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("category", sa.Text, nullable=False),
        sa.Column("title", sa.Text, nullable=False),
        sa.Column("description", sa.Text),
        sa.Column("conversation_id", sa.Text),
        sa.Column("status", sa.Text, nullable=False, server_default="open"),
        sa.Column("notion_page_id", sa.Text),
    )
    op.create_index("idx_wishlist_category", "wishlist", ["category"])
    op.create_index("idx_wishlist_status", "wishlist", ["status"])

    op.create_table("schema_version", sa.Column("version", sa.Integer, primary_key=True))

    op.create_table(
        "matomo_baselines",
        sa.Column("site_id", sa.Integer, primary_key=True),
        sa.Column("month", sa.Text, primary_key=True),
        sa.Column("visitors", sa.Integer),
        sa.Column("visits", sa.Integer),
        sa.Column("daily_avg_visitors", sa.Integer),
        sa.Column("daily_avg_visits", sa.Integer),
        sa.Column("bounce_rate", sa.Text),
        sa.Column("actions_per_visit", sa.Integer),
        sa.Column("avg_time_on_site", sa.Integer),
        sa.Column("user_types", postgresql.JSONB),
        sa.Column("synced_at", sa.DateTime, server_default=sa.func.now()),
    )

    op.create_table(
        "matomo_dimensions",
        sa.Column("site_id", sa.Integer, primary_key=True),
        sa.Column("dimension_id", sa.Integer, primary_key=True),
        sa.Column("name", sa.Text, nullable=False),
        sa.Column("scope", sa.Text),
        sa.Column("active", sa.Boolean, server_default="true"),
        sa.Column("synced_at", sa.DateTime, server_default=sa.func.now()),
    )

    op.create_table(
        "matomo_segments",
        sa.Column("site_id", sa.Integer, primary_key=True),
        sa.Column("name", sa.Text, primary_key=True),
        sa.Column("definition", sa.Text),
        sa.Column("synced_at", sa.DateTime, server_default=sa.func.now()),
    )

    op.create_table(
        "matomo_events",
        sa.Column("site_id", sa.Integer, primary_key=True),
        sa.Column("name", sa.Text, primary_key=True),
        sa.Column("reference_month", sa.Text, primary_key=True),
        sa.Column("event_count", sa.Integer, server_default="0"),
        sa.Column("visit_count", sa.Integer, server_default="0"),
        sa.Column("synced_at", sa.DateTime, server_default=sa.func.now()),
    )

    op.create_table(
        "metabase_cards",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("instance", sa.Text, primary_key=True),
        sa.Column("name", sa.Text),
        sa.Column("description", sa.Text),
        sa.Column("collection_id", sa.Integer),
        sa.Column("dashboard_id", sa.Integer),
        sa.Column("dashboard_name", sa.Text),
        sa.Column("topic", sa.Text),
        sa.Column("sql_query", sa.Text),
        sa.Column("tables_json", sa.Text),
        sa.Column("synced_at", sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index("idx_metabase_cards_topic", "metabase_cards", ["instance", "topic"])
    op.create_index("idx_metabase_cards_dashboard", "metabase_cards", ["instance", "dashboard_id"])

    op.create_table(
        "metabase_dashboards",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("instance", sa.Text, primary_key=True),
        sa.Column("name", sa.Text),
        sa.Column("description", sa.Text),
        sa.Column("topic", sa.Text),
        sa.Column("pilotage_url", sa.Text),
        sa.Column("collection_id", sa.Integer),
        sa.Column("synced_at", sa.DateTime, server_default=sa.func.now()),
    )


def downgrade() -> None:
    for table in reversed(TABLES):
        op.drop_table(table)
