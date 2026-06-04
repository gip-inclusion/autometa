"""SQLAlchemy models — single source of truth for the database schema."""

from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Conversation(Base):
    __tablename__ = "conversations"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    user_id: Mapped[str | None] = mapped_column(Text)
    title: Mapped[str | None] = mapped_column(Text)
    session_id: Mapped[str | None] = mapped_column(Text)
    conv_type: Mapped[str] = mapped_column(Text, default="exploration")
    file_path: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(Text, default="active")
    pr_url: Mapped[str | None] = mapped_column(Text)
    forked_from: Mapped[str | None] = mapped_column(Text)
    usage_input_tokens: Mapped[int] = mapped_column(Integer, default=0)
    usage_output_tokens: Mapped[int] = mapped_column(Integer, default=0)
    usage_cache_creation_tokens: Mapped[int] = mapped_column(Integer, default=0)
    usage_cache_read_tokens: Mapped[int] = mapped_column(Integer, default=0)
    usage_backend: Mapped[str | None] = mapped_column(Text)
    usage_extra: Mapped[str | None] = mapped_column(Text)
    pinned_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    pinned_label: Mapped[str | None] = mapped_column(Text)
    flagged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    flag_reason: Mapped[str | None] = mapped_column(Text)
    flag_user_id: Mapped[str | None] = mapped_column(Text)
    needs_response: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    messages: Mapped[list["Message"]] = relationship(back_populates="conversation", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_conversations_updated", "updated_at"),
        Index("idx_conversations_type_status", "conv_type", "status"),
        Index("idx_conversations_user_updated", "user_id", "updated_at"),
        Index("idx_conversations_needs_response", "needs_response", postgresql_where="needs_response = 1"),
        Index("idx_conversations_flagged", "flagged_at", postgresql_where="flagged_at IS NOT NULL"),
    )


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    conversation_id: Mapped[str] = mapped_column(Text, ForeignKey("conversations.id"), nullable=False)
    type: Mapped[str | None] = mapped_column(Text)
    role: Mapped[str] = mapped_column(Text, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    raw_events: Mapped[str | None] = mapped_column(Text)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    conversation: Mapped["Conversation"] = relationship(back_populates="messages")

    __table_args__ = (
        Index("idx_messages_conversation", "conversation_id"),
        Index("idx_messages_conv_id", "conversation_id", "id"),
    )


class Report(Base):
    __tablename__ = "reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    content: Mapped[str | None] = mapped_column(Text)
    website: Mapped[str | None] = mapped_column(Text)
    category: Mapped[str | None] = mapped_column(Text)
    tags: Mapped[str | None] = mapped_column(Text)
    original_query: Mapped[str | None] = mapped_column(Text)
    source_conversation_id: Mapped[str | None] = mapped_column(Text)
    user_id: Mapped[str | None] = mapped_column(Text)
    version: Mapped[int] = mapped_column(Integer, default=1)
    archived: Mapped[int] = mapped_column(Integer, default=0)
    notion_url: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    conversation_id: Mapped[str | None] = mapped_column(Text)
    message_id: Mapped[int | None] = mapped_column(Integer)

    __table_args__ = (Index("idx_reports_updated", "updated_at"),)


class Tag(Base):
    __tablename__ = "tags"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    type: Mapped[str] = mapped_column(Text, nullable=False)
    label: Mapped[str] = mapped_column(Text, nullable=False)

    __table_args__ = (Index("idx_tags_type", "type"),)


class ConversationTag(Base):
    __tablename__ = "conversation_tags"

    conversation_id: Mapped[str] = mapped_column(
        Text, ForeignKey("conversations.id", ondelete="CASCADE"), primary_key=True
    )
    tag_id: Mapped[int] = mapped_column(Integer, ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True)

    __table_args__ = (
        Index("idx_conversation_tags_conv", "conversation_id"),
        Index("idx_conversation_tags_tag", "tag_id"),
    )


class ReportTag(Base):
    __tablename__ = "report_tags"

    report_id: Mapped[int] = mapped_column(Integer, ForeignKey("reports.id", ondelete="CASCADE"), primary_key=True)
    tag_id: Mapped[int] = mapped_column(Integer, ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True)

    __table_args__ = (
        Index("idx_report_tags_report", "report_id"),
        Index("idx_report_tags_tag", "tag_id"),
    )


class Dashboard(Base):
    __tablename__ = "dashboards"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    slug: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    website: Mapped[str | None] = mapped_column(Text)
    category: Mapped[str | None] = mapped_column(Text)
    first_author_email: Mapped[str] = mapped_column(Text, nullable=False)
    created_in_conversation_id: Mapped[str | None] = mapped_column(Text)
    is_archived: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    has_api_access: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    has_cron: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    has_persistence: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class DashboardTag(Base):
    __tablename__ = "dashboard_tags"

    dashboard_slug: Mapped[str] = mapped_column(
        Text, ForeignKey("dashboards.slug", ondelete="CASCADE"), primary_key=True
    )
    tag_id: Mapped[int] = mapped_column(Integer, ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True)

    __table_args__ = (
        Index("idx_dashboard_tags_slug", "dashboard_slug"),
        Index("idx_dashboard_tags_tag", "tag_id"),
    )


class DashboardPublication(Base):
    __tablename__ = "dashboard_publications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    dashboard_slug: Mapped[str] = mapped_column(Text, ForeignKey("dashboards.slug", ondelete="CASCADE"), nullable=False)
    publication_id: Mapped[str] = mapped_column(Text, nullable=False)
    environment: Mapped[str] = mapped_column(Text, nullable=False)
    published_by: Mapped[str] = mapped_column(Text, nullable=False)
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    unpublished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    snapshot_has_cron: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    refresh_paused_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_successful_refresh_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_refresh_status: Mapped[str | None] = mapped_column(Text)
    last_refresh_error: Mapped[str | None] = mapped_column(Text)

    __table_args__ = (
        Index("idx_dashboard_publications_slug", "dashboard_slug"),
        Index(
            "idx_dashboard_publications_refreshable",
            "snapshot_has_cron",
            "unpublished_at",
            "refresh_paused_at",
        ),
        UniqueConstraint("publication_id", name="uq_dashboard_publications_publication_id"),
    )


class UploadedFile(Base):
    __tablename__ = "uploaded_files"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    conversation_id: Mapped[str | None] = mapped_column(Text, ForeignKey("conversations.id", ondelete="CASCADE"))
    user_id: Mapped[str | None] = mapped_column(Text)
    original_filename: Mapped[str] = mapped_column(Text, nullable=False)
    stored_filename: Mapped[str] = mapped_column(Text, nullable=False)
    storage_path: Mapped[str] = mapped_column(Text, nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)
    mime_type: Mapped[str | None] = mapped_column(Text)
    sha256_hash: Mapped[str] = mapped_column(Text, nullable=False)
    is_text: Mapped[bool] = mapped_column(Boolean, default=False)
    av_scanned: Mapped[bool] = mapped_column(Boolean, default=False)
    av_clean: Mapped[bool | None] = mapped_column(Boolean)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        Index("idx_uploaded_files_conversation", "conversation_id"),
        Index("idx_uploaded_files_hash", "sha256_hash"),
        Index("idx_uploaded_files_user", "user_id"),
    )


class CronRun(Base):
    __tablename__ = "cron_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    app_slug: Mapped[str] = mapped_column(Text, nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(Text, nullable=False)
    output: Mapped[str | None] = mapped_column(Text)
    duration_ms: Mapped[int | None] = mapped_column(Integer)
    trigger: Mapped[str] = mapped_column(Text, nullable=False, default="scheduled")

    __table_args__ = (Index("idx_cron_runs_slug_started", "app_slug", "started_at"),)


class PinnedItem(Base):
    __tablename__ = "pinned_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    item_type: Mapped[str] = mapped_column(Text, nullable=False)
    item_id: Mapped[str] = mapped_column(Text, nullable=False)
    label: Mapped[str | None] = mapped_column(Text)
    pinned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (UniqueConstraint("item_type", "item_id"),)


class PmCommand(Base):
    __tablename__ = "pm_commands"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    conversation_id: Mapped[str] = mapped_column(Text, nullable=False)
    command: Mapped[str] = mapped_column(Text, nullable=False)
    payload: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (Index("idx_pm_commands_pending", "processed_at", postgresql_where="processed_at IS NULL"),)


class PmHeartbeat(Base):
    __tablename__ = "pm_heartbeat"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    last_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class SchemaVersion(Base):
    __tablename__ = "schema_version"

    version: Mapped[int] = mapped_column(Integer, primary_key=True)


class MatomoBaseline(Base):
    __tablename__ = "matomo_baselines"

    site_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    month: Mapped[str] = mapped_column(Text, primary_key=True)
    visitors: Mapped[int | None] = mapped_column(Integer)
    visits: Mapped[int | None] = mapped_column(Integer)
    daily_avg_visitors: Mapped[int | None] = mapped_column(Integer)
    daily_avg_visits: Mapped[int | None] = mapped_column(Integer)
    bounce_rate: Mapped[str | None] = mapped_column(Text)
    actions_per_visit: Mapped[float | None] = mapped_column(Integer)
    avg_time_on_site: Mapped[int | None] = mapped_column(Integer)
    user_types: Mapped[dict | None] = mapped_column(JSONB)
    synced_at: Mapped[datetime | None] = mapped_column(DateTime, server_default=func.now())


class MatomoDimension(Base):
    __tablename__ = "matomo_dimensions"

    site_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    dimension_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    scope: Mapped[str | None] = mapped_column(Text)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    synced_at: Mapped[datetime | None] = mapped_column(DateTime, server_default=func.now())


class MatomoSegment(Base):
    __tablename__ = "matomo_segments"

    site_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(Text, primary_key=True)
    definition: Mapped[str | None] = mapped_column(Text)
    synced_at: Mapped[datetime | None] = mapped_column(DateTime, server_default=func.now())


class MatomoEvent(Base):
    __tablename__ = "matomo_events"

    site_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(Text, primary_key=True)
    reference_month: Mapped[str] = mapped_column(Text, primary_key=True)
    event_count: Mapped[int] = mapped_column(Integer, default=0)
    visit_count: Mapped[int] = mapped_column(Integer, default=0)
    synced_at: Mapped[datetime | None] = mapped_column(DateTime, server_default=func.now())


class MetabaseCard(Base):
    __tablename__ = "metabase_cards"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    instance: Mapped[str] = mapped_column(Text, primary_key=True)
    name: Mapped[str | None] = mapped_column(Text)
    description: Mapped[str | None] = mapped_column(Text)
    collection_id: Mapped[int | None] = mapped_column(Integer)
    dashboard_id: Mapped[int | None] = mapped_column(Integer)
    dashboard_name: Mapped[str | None] = mapped_column(Text)
    topic: Mapped[str | None] = mapped_column(Text)
    sql_query: Mapped[str | None] = mapped_column(Text)
    tables_json: Mapped[str | None] = mapped_column(Text)
    synced_at: Mapped[datetime | None] = mapped_column(DateTime, server_default=func.now())

    __table_args__ = (
        Index("idx_metabase_cards_topic", "instance", "topic"),
        Index("idx_metabase_cards_dashboard", "instance", "dashboard_id"),
    )


class MetabaseDashboard(Base):
    __tablename__ = "metabase_dashboards"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    instance: Mapped[str] = mapped_column(Text, primary_key=True)
    name: Mapped[str | None] = mapped_column(Text)
    description: Mapped[str | None] = mapped_column(Text)
    topic: Mapped[str | None] = mapped_column(Text)
    pilotage_url: Mapped[str | None] = mapped_column(Text)
    collection_id: Mapped[int | None] = mapped_column(Integer)
    synced_at: Mapped[datetime | None] = mapped_column(DateTime, server_default=func.now())


class UsageEvent(Base):
    __tablename__ = "usage_events"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    conversation_id: Mapped[str | None] = mapped_column(Text, ForeignKey("conversations.id", ondelete="SET NULL"))
    cli_message_id: Mapped[str | None] = mapped_column(Text)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    kind: Mapped[str] = mapped_column(Text, nullable=False, default="turn")
    model: Mapped[str | None] = mapped_column(Text)
    backend: Mapped[str] = mapped_column(Text, nullable=False)
    service_tier: Mapped[str | None] = mapped_column(Text)
    input_tokens: Mapped[int] = mapped_column(Integer, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, default=0)
    cache_creation_5m_tokens: Mapped[int] = mapped_column(Integer, default=0)
    cache_creation_1h_tokens: Mapped[int] = mapped_column(Integer, default=0)
    cache_read_tokens: Mapped[int] = mapped_column(Integer, default=0)
    web_search_requests: Mapped[int] = mapped_column(Integer, default=0)
    web_fetch_requests: Mapped[int] = mapped_column(Integer, default=0)
    raw: Mapped[dict | None] = mapped_column(JSONB)

    __table_args__ = (
        Index("idx_usage_events_conv_ts", "conversation_id", "timestamp"),
        Index("idx_usage_events_ts", "timestamp"),
        Index("idx_usage_events_kind_ts", "kind", "timestamp"),
    )
