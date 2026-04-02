"""SQLAlchemy models — single source of truth for the database schema."""

from datetime import datetime

from sqlalchemy import (
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


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    user_id: Mapped[str | None] = mapped_column(Text)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    slug: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    description: Mapped[str | None] = mapped_column(Text)
    spec: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(Text, default="draft")
    workflow_phase: Mapped[str] = mapped_column(Text, default="planning")
    gitea_repo_id: Mapped[int | None] = mapped_column(Integer)
    gitea_url: Mapped[str | None] = mapped_column(Text)
    staging_branch: Mapped[str] = mapped_column(Text, default="staging")
    production_branch: Mapped[str] = mapped_column(Text, default="prod")
    staging_deploy_url: Mapped[str | None] = mapped_column(Text)
    production_deploy_url: Mapped[str | None] = mapped_column(Text)
    tech_stack: Mapped[str | None] = mapped_column(Text)
    boilerplate: Mapped[str | None] = mapped_column(Text)
    scaleway_container_id: Mapped[str | None] = mapped_column(Text)
    scaleway_url: Mapped[str | None] = mapped_column(Text)
    scaleway_db_url: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[str] = mapped_column(Text, nullable=False)

    __table_args__ = (
        Index("idx_projects_user", "user_id"),
        Index("idx_projects_slug", "slug"),
    )


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
    project_id: Mapped[str | None] = mapped_column(Text, ForeignKey("projects.id"))
    usage_input_tokens: Mapped[int] = mapped_column(Integer, default=0)
    usage_output_tokens: Mapped[int] = mapped_column(Integer, default=0)
    usage_cache_creation_tokens: Mapped[int] = mapped_column(Integer, default=0)
    usage_cache_read_tokens: Mapped[int] = mapped_column(Integer, default=0)
    usage_backend: Mapped[str | None] = mapped_column(Text)
    usage_extra: Mapped[str | None] = mapped_column(Text)
    pinned_at: Mapped[str | None] = mapped_column(Text)
    pinned_label: Mapped[str | None] = mapped_column(Text)
    needs_response: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[str] = mapped_column(Text, nullable=False)

    messages: Mapped[list["Message"]] = relationship(back_populates="conversation", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_conversations_updated", "updated_at", postgresql_ops={"updated_at": "DESC"}),
        Index("idx_conversations_type_status", "conv_type", "status"),
        Index("idx_conversations_user_updated", "user_id", "updated_at", postgresql_ops={"updated_at": "DESC"}),
        Index("idx_conversations_needs_response", "needs_response", postgresql_where="needs_response = 1"),
        Index("idx_conversations_project", "project_id"),
    )


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    conversation_id: Mapped[str] = mapped_column(Text, ForeignKey("conversations.id"), nullable=False)
    type: Mapped[str | None] = mapped_column(Text)
    role: Mapped[str] = mapped_column(Text, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    raw_events: Mapped[str | None] = mapped_column(Text)
    timestamp: Mapped[str] = mapped_column(Text, nullable=False)

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
    created_at: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[str] = mapped_column(Text, nullable=False)
    conversation_id: Mapped[str | None] = mapped_column(Text)
    message_id: Mapped[int | None] = mapped_column(Integer)

    __table_args__ = (Index("idx_reports_updated", "updated_at", postgresql_ops={"updated_at": "DESC"}),)


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
    created_at: Mapped[str] = mapped_column(Text, nullable=False)

    __table_args__ = (
        Index("idx_uploaded_files_conversation", "conversation_id"),
        Index("idx_uploaded_files_hash", "sha256_hash"),
        Index("idx_uploaded_files_user", "user_id"),
    )


class CronRun(Base):
    __tablename__ = "cron_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    app_slug: Mapped[str] = mapped_column(Text, nullable=False)
    started_at: Mapped[str] = mapped_column(Text, nullable=False)
    finished_at: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(Text, nullable=False)
    output: Mapped[str | None] = mapped_column(Text)
    duration_ms: Mapped[int | None] = mapped_column(Integer)
    trigger: Mapped[str] = mapped_column(Text, nullable=False, default="scheduled")

    __table_args__ = (
        Index("idx_cron_runs_slug_started", "app_slug", "started_at", postgresql_ops={"started_at": "DESC"}),
    )


class PinnedItem(Base):
    __tablename__ = "pinned_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    item_type: Mapped[str] = mapped_column(Text, nullable=False)
    item_id: Mapped[str] = mapped_column(Text, nullable=False)
    label: Mapped[str | None] = mapped_column(Text)
    pinned_at: Mapped[str] = mapped_column(Text, nullable=False)

    __table_args__ = (UniqueConstraint("item_type", "item_id"),)


class PmCommand(Base):
    __tablename__ = "pm_commands"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    conversation_id: Mapped[str] = mapped_column(Text, nullable=False)
    command: Mapped[str] = mapped_column(Text, nullable=False)
    payload: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[str] = mapped_column(Text, nullable=False)
    processed_at: Mapped[str | None] = mapped_column(Text)

    __table_args__ = (Index("idx_pm_commands_pending", "processed_at", postgresql_where="processed_at IS NULL"),)


class PmHeartbeat(Base):
    __tablename__ = "pm_heartbeat"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    last_seen: Mapped[str] = mapped_column(Text, nullable=False)


class Wishlist(Base):
    __tablename__ = "wishlist"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    category: Mapped[str] = mapped_column(Text, nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    conversation_id: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(Text, nullable=False, default="open")
    notion_page_id: Mapped[str | None] = mapped_column(Text)

    __table_args__ = (
        Index("idx_wishlist_category", "category"),
        Index("idx_wishlist_status", "status"),
    )


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


class Recette(Base):
    __tablename__ = "recettes"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    user_id: Mapped[str | None] = mapped_column(Text)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    slug: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    github_repo: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, default="cloned")
    project_id: Mapped[str | None] = mapped_column(Text, ForeignKey("projects.id"))
    branch_a: Mapped[str] = mapped_column(Text, default="main")
    branch_b: Mapped[str | None] = mapped_column(Text)
    port_a: Mapped[int | None] = mapped_column(Integer)
    port_b: Mapped[int | None] = mapped_column(Integer)
    deploy_url_a: Mapped[str | None] = mapped_column(Text)
    deploy_url_b: Mapped[str | None] = mapped_column(Text)
    pr_url: Mapped[str | None] = mapped_column(Text)
    pr_status: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[str] = mapped_column(Text, nullable=False)

    __table_args__ = (
        Index("idx_recettes_user", "user_id"),
        Index("idx_recettes_slug", "slug"),
    )
