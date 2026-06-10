"""Dataclass records and converters shared by the domain store mixins."""

import json
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from web.helpers import utcnow
from web.models import Message as MsgModel
from web.models import Report as ReportModel
from web.models import Tag as TagModel
from web.models import UploadedFile as FileModel

VALID_CONVERSATION_COLUMNS = frozenset({
    "title",
    "session_id",
    "user_id",
    "status",
    "pr_url",
    "needs_response",
    "updated_at",
    "conv_type",
    "file_path",
    "forked_from",
    "usage_input_tokens",
    "usage_output_tokens",
    "usage_cache_creation_tokens",
    "usage_cache_read_tokens",
    "usage_backend",
    "usage_extra",
    "pinned_at",
    "pinned_label",
})

VALID_REPORT_COLUMNS = frozenset({
    "title",
    "content",
    "website",
    "category",
    "tags",
    "original_query",
    "source_conversation_id",
    "user_id",
    "archived",
    "notion_url",
    "updated_at",
    "version",
    "conversation_id",
    "message_id",
})


def build_update_clause(updates: dict, valid_columns: frozenset) -> tuple[str, list]:
    """Build a safe SET clause from a dict of updates, validating column names."""
    if not updates:
        return "", []
    for col in updates:
        if col not in valid_columns:
            raise ValueError(f"Invalid column name: {col}")
    parts = [f"{col} = %s" for col in updates]
    return ", ".join(parts), list(updates.values())


@dataclass
class Tag:
    """A tag for categorizing conversations and reports."""

    id: Optional[int] = None
    name: str = ""
    type: str = ""
    label: str = ""
    count: int = 0


@dataclass
class PinnedItem:
    """A pinned item (conversation, report, or app)."""

    id: Optional[int] = None
    item_type: str = ""
    item_id: str = ""
    label: str = ""
    pinned_at: Optional[datetime] = None


@dataclass
class UploadedFile:
    """A file uploaded to a conversation."""

    id: Optional[int] = None
    conversation_id: Optional[str] = None
    user_id: Optional[str] = None
    original_filename: str = ""
    stored_filename: str = ""
    storage_path: str = ""
    file_size: int = 0
    mime_type: Optional[str] = None
    sha256_hash: str = ""
    is_text: bool = False
    av_scanned: bool = False
    av_clean: Optional[bool] = None
    created_at: datetime = field(default_factory=utcnow)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "conversation_id": self.conversation_id,
            "user_id": self.user_id,
            "original_filename": self.original_filename,
            "stored_filename": self.stored_filename,
            "storage_path": self.storage_path,
            "file_size": self.file_size,
            "mime_type": self.mime_type,
            "sha256_hash": self.sha256_hash,
            "is_text": self.is_text,
            "av_scanned": self.av_scanned,
            "av_clean": self.av_clean,
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class Message:
    """A single message in a conversation."""

    id: Optional[int] = None
    conversation_id: Optional[str] = None
    type: str = "user"
    content: str = ""
    created_at: datetime = field(default_factory=utcnow)


@dataclass
class Report:
    """A report with its content."""

    id: Optional[int] = None
    title: str = ""
    content: Optional[str] = None
    website: Optional[str] = None
    category: Optional[str] = None
    tags: list[str] = field(default_factory=list)
    original_query: Optional[str] = None
    source_conversation_id: Optional[str] = None
    user_id: Optional[str] = None
    archived: bool = False
    notion_url: Optional[str] = None
    version: int = 1
    created_at: datetime = field(default_factory=utcnow)
    updated_at: datetime = field(default_factory=utcnow)
    conversation_id: Optional[str] = None
    message_id: Optional[int] = None


@dataclass
class Conversation:
    """A conversation with its messages and optional report."""

    id: str = ""
    user_id: Optional[str] = None
    title: Optional[str] = None
    session_id: Optional[str] = None
    conv_type: str = "exploration"
    file_path: Optional[str] = None
    status: str = "active"
    pr_url: Optional[str] = None
    forked_from: Optional[str] = None
    messages: list[Message] = field(default_factory=list)
    report: Optional[Report] = None
    usage_input_tokens: int = 0
    usage_output_tokens: int = 0
    usage_cache_creation_tokens: int = 0
    usage_cache_read_tokens: int = 0
    usage_backend: Optional[str] = None
    usage_extra: Optional[dict] = None
    pinned_at: Optional[datetime] = None
    pinned_label: Optional[str] = None
    flagged_at: Optional[datetime] = None
    flag_reason: Optional[str] = None
    flag_user_id: Optional[str] = None
    needs_response: bool = False
    created_at: datetime = field(default_factory=utcnow)
    updated_at: datetime = field(default_factory=utcnow)

    @property
    def has_report(self) -> bool:
        return self.report is not None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "title": self.title,
            "session_id": self.session_id,
            "conv_type": self.conv_type,
            "file_path": self.file_path,
            "status": self.status,
            "pr_url": self.pr_url,
            "has_report": self.has_report,
            "usage_input_tokens": self.usage_input_tokens,
            "usage_output_tokens": self.usage_output_tokens,
            "usage_cache_creation_tokens": self.usage_cache_creation_tokens,
            "usage_cache_read_tokens": self.usage_cache_read_tokens,
            "usage_backend": self.usage_backend,
            "usage_extra": self.usage_extra,
            "pinned_at": self.pinned_at.isoformat() if self.pinned_at else None,
            "pinned_label": self.pinned_label,
            "flagged_at": self.flagged_at.isoformat() if self.flagged_at else None,
            "flag_reason": self.flag_reason,
            "flag_user_id": self.flag_user_id,
            "messages": [
                {
                    "id": m.id,
                    "type": m.type,
                    "content": m.content,
                    "created_at": m.created_at.isoformat(),
                }
                for m in self.messages
            ],
            "report": {
                "id": self.report.id,
                "title": self.report.title,
                "website": self.report.website,
                "category": self.report.category,
                "tags": self.report.tags,
                "version": self.report.version,
            }
            if self.report
            else None,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


def model_to_report(r: ReportModel) -> Report:
    return Report(
        id=r.id,
        title=r.title,
        website=r.website,
        category=r.category,
        tags=json.loads(r.tags) if r.tags else [],
        original_query=r.original_query,
        source_conversation_id=r.source_conversation_id,
        user_id=r.user_id,
        archived=bool(r.archived),
        notion_url=r.notion_url,
        version=r.version,
        created_at=r.created_at,
        updated_at=r.updated_at,
        conversation_id=r.conversation_id,
        message_id=r.message_id,
    )


def model_to_tag(t: TagModel, count: int = 0) -> Tag:
    return Tag(id=t.id, name=t.name, type=t.type, label=t.label, count=count)


def model_to_uploaded_file(f: FileModel) -> UploadedFile:
    return UploadedFile(
        id=f.id,
        conversation_id=f.conversation_id,
        user_id=f.user_id,
        original_filename=f.original_filename,
        stored_filename=f.stored_filename,
        storage_path=f.storage_path,
        file_size=f.file_size,
        mime_type=f.mime_type,
        sha256_hash=f.sha256_hash,
        is_text=bool(f.is_text),
        av_scanned=bool(f.av_scanned),
        av_clean=bool(f.av_clean) if f.av_clean is not None else None,
        created_at=f.created_at,
    )


def model_to_message(m: MsgModel) -> Message:
    return Message(
        id=m.id,
        conversation_id=m.conversation_id,
        type=m.type or m.role,
        content=m.content,
        created_at=m.timestamp,
    )


def conv_with_report_row(row, report_id, report_title) -> Conversation:
    return Conversation(
        id=row.id,
        user_id=row.user_id,
        title=row.title,
        session_id=row.session_id,
        conv_type=row.conv_type or "exploration",
        file_path=row.file_path,
        status=row.status or "active",
        needs_response=bool(row.needs_response) if row.needs_response else False,
        messages=[],
        report=Report(id=report_id, title=report_title or "") if report_id else None,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )
