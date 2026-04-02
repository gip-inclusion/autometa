"""Database models and ConversationStore for conversation/report persistence."""

import json
import random
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from sqlalchemy import func, select, text

from .db import get_db, init_tables
from .models import Conversation as ConvModel
from .models import ConversationTag as ConvTagModel
from .models import Message as MsgModel
from .models import PinnedItem as PinModel
from .models import Project as ProjectModel
from .models import Report as ReportModel
from .models import ReportTag as ReportTagModel
from .models import Tag as TagModel
from .models import UploadedFile as FileModel

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
    "project_id",
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


def init_db():
    """Backward-compatible alias for init_tables()."""
    init_tables()


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
    created_at: datetime = field(default_factory=datetime.now)

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
    created_at: datetime = field(default_factory=datetime.now)


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
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
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
    project_id: Optional[str] = None
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
    needs_response: bool = False
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

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
            "project_id": self.project_id,
            "has_report": self.has_report,
            "usage_input_tokens": self.usage_input_tokens,
            "usage_output_tokens": self.usage_output_tokens,
            "usage_cache_creation_tokens": self.usage_cache_creation_tokens,
            "usage_cache_read_tokens": self.usage_cache_read_tokens,
            "usage_backend": self.usage_backend,
            "usage_extra": self.usage_extra,
            "pinned_at": self.pinned_at.isoformat() if self.pinned_at else None,
            "pinned_label": self.pinned_label,
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


def _model_to_report(r: ReportModel) -> Report:
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
        created_at=datetime.fromisoformat(r.created_at),
        updated_at=datetime.fromisoformat(r.updated_at),
        conversation_id=r.conversation_id,
        message_id=r.message_id,
    )


def _model_to_tag(t: TagModel, count: int = 0) -> Tag:
    return Tag(id=t.id, name=t.name, type=t.type, label=t.label, count=count)


def _model_to_uploaded_file(f: FileModel) -> UploadedFile:
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
        created_at=datetime.fromisoformat(f.created_at),
    )


def _model_to_message(m: MsgModel) -> Message:
    return Message(
        id=m.id,
        conversation_id=m.conversation_id,
        type=m.type or m.role,
        content=m.content,
        created_at=datetime.fromisoformat(m.timestamp),
    )


def _conv_with_report_row(row, report_id, report_title) -> Conversation:
    return Conversation(
        id=row.id,
        user_id=row.user_id,
        title=row.title,
        session_id=row.session_id,
        conv_type=row.conv_type or "exploration",
        file_path=row.file_path,
        status=row.status or "active",
        project_id=getattr(row, "project_id", None),
        needs_response=bool(row.needs_response) if row.needs_response else False,
        messages=[],
        report=Report(id=report_id, title=report_title or "") if report_id else None,
        created_at=datetime.fromisoformat(row.created_at),
        updated_at=datetime.fromisoformat(row.updated_at),
    )


class ConversationStore:
    """PostgreSQL-backed conversation and report store."""

    def __init__(self):
        init_tables()

    def create_conversation(
        self,
        user_id: Optional[str] = None,
        conv_type: str = "exploration",
        file_path: Optional[str] = None,
        project_id: Optional[str] = None,
    ) -> Conversation:
        conv = Conversation(
            id=str(uuid.uuid4()),
            user_id=user_id,
            conv_type=conv_type,
            file_path=file_path,
            project_id=project_id,
        )

        with get_db() as session:
            model = ConvModel(
                id=conv.id,
                user_id=conv.user_id,
                title=conv.title,
                session_id=conv.session_id,
                conv_type=conv.conv_type,
                file_path=conv.file_path,
                project_id=conv.project_id,
                status=conv.status,
                created_at=conv.created_at.isoformat(),
                updated_at=conv.updated_at.isoformat(),
            )
            session.add(model)

        return conv

    def get_conversation(
        self, conv_id: str, include_messages: bool = True, user_id: Optional[str] = None
    ) -> Optional[Conversation]:
        with get_db() as session:
            stmt = (
                select(ConvModel, PinModel.pinned_at, PinModel.label)
                .outerjoin(PinModel, (PinModel.item_id == ConvModel.id) & (PinModel.item_type == "conversation"))
                .where(ConvModel.id == conv_id)
            )
            if user_id:
                stmt = stmt.where(ConvModel.user_id == user_id)

            row = session.execute(stmt).first()
            if not row:
                return None

            c, p_pinned_at, p_label = row

            messages = []
            if include_messages:
                msg_models = session.scalars(
                    select(MsgModel).where(MsgModel.conversation_id == conv_id).order_by(MsgModel.timestamp)
                ).all()
                messages = [_model_to_message(m) for m in msg_models]

            report_model = session.scalars(select(ReportModel).where(ReportModel.conversation_id == conv_id)).first()

            report = None
            if report_model:
                report = _model_to_report(report_model)

            usage_extra = None
            if c.usage_extra:
                usage_extra = json.loads(c.usage_extra)

            return Conversation(
                id=c.id,
                user_id=c.user_id,
                title=c.title,
                session_id=c.session_id,
                conv_type=c.conv_type or "exploration",
                file_path=c.file_path,
                status=c.status or "active",
                pr_url=c.pr_url,
                forked_from=c.forked_from,
                project_id=c.project_id,
                messages=messages,
                report=report,
                usage_input_tokens=c.usage_input_tokens or 0,
                usage_output_tokens=c.usage_output_tokens or 0,
                usage_cache_creation_tokens=c.usage_cache_creation_tokens or 0,
                usage_cache_read_tokens=c.usage_cache_read_tokens or 0,
                usage_backend=c.usage_backend,
                usage_extra=usage_extra,
                pinned_at=datetime.fromisoformat(p_pinned_at) if p_pinned_at else None,
                pinned_label=p_label,
                needs_response=bool(c.needs_response) if c.needs_response else False,
                created_at=datetime.fromisoformat(c.created_at),
                updated_at=datetime.fromisoformat(c.updated_at),
            )

    def fork_conversation(self, source_conv_id: str, new_user_id: str) -> Optional[Conversation]:
        """Deep copy a conversation for a new user."""
        source = self.get_conversation(source_conv_id, include_messages=True)
        if not source:
            return None

        now = datetime.now()
        new_id = str(uuid.uuid4())

        with get_db() as session:
            model = ConvModel(
                id=new_id,
                user_id=new_user_id,
                title=source.title,
                session_id=None,
                conv_type=source.conv_type,
                file_path=source.file_path,
                status="active",
                forked_from=source_conv_id,
                created_at=now.isoformat(),
                updated_at=now.isoformat(),
            )
            session.add(model)

            for msg in source.messages:
                session.add(
                    MsgModel(
                        conversation_id=new_id,
                        type=msg.type,
                        role=msg.type,
                        content=msg.content,
                        timestamp=msg.created_at.isoformat(),
                    )
                )

        return self.get_conversation(new_id, include_messages=True)

    def list_conversations(
        self,
        user_id: Optional[str] = None,
        limit: int = 50,
        conv_type: Optional[str] = None,
        exclude_report_containers: bool = True,
    ) -> list[Conversation]:
        with get_db() as session:
            conditions = []
            params: dict = {}

            if user_id:
                conditions.append("c.user_id = :user_id")
                params["user_id"] = user_id

            if conv_type:
                conditions.append("c.conv_type = :conv_type")
                params["conv_type"] = conv_type
            else:
                conditions.append("(c.conv_type = 'exploration' OR c.conv_type IS NULL)")

            if exclude_report_containers:
                conditions.append("r.id IS NULL")

            where = "WHERE " + " AND ".join(conditions) if conditions else ""
            params["lim"] = limit

            query = text(f"""
                SELECT c.*, r.id as report_id, r.title as report_title
                FROM conversations c
                LEFT JOIN reports r ON r.conversation_id = c.id
                {where}
                ORDER BY c.updated_at DESC
                LIMIT :lim
            """)

            rows = session.execute(query, params).mappings().all()
            return [_conv_with_report_row(row, row["report_id"], row["report_title"]) for row in rows]

    def pin_item(self, item_type: str, item_id: str, label: str) -> bool:
        with get_db() as session:
            now = datetime.now().isoformat()
            existing = session.scalars(
                select(PinModel).where(PinModel.item_type == item_type, PinModel.item_id == str(item_id))
            ).first()
            if existing:
                existing.label = label
                existing.pinned_at = now
            else:
                session.add(
                    PinModel(
                        item_type=item_type,
                        item_id=str(item_id),
                        label=label,
                        pinned_at=now,
                    )
                )
            return True

    def unpin_item(self, item_type: str, item_id: str) -> bool:
        with get_db() as session:
            existing = session.scalars(
                select(PinModel).where(PinModel.item_type == item_type, PinModel.item_id == str(item_id))
            ).first()
            if existing:
                session.delete(existing)
                return True
            return False

    def list_pinned_items(self, item_type: Optional[str] = None) -> list[PinnedItem]:
        with get_db() as session:
            stmt = select(PinModel).order_by(PinModel.pinned_at)
            if item_type:
                stmt = stmt.where(PinModel.item_type == item_type)
            models = session.scalars(stmt).all()
            return [
                PinnedItem(
                    id=m.id,
                    item_type=m.item_type,
                    item_id=m.item_id,
                    label=m.label,
                    pinned_at=datetime.fromisoformat(m.pinned_at),
                )
                for m in models
            ]

    def get_pinned_ids(self) -> set[tuple[str, str]]:
        with get_db() as session:
            rows = session.execute(select(PinModel.item_type, PinModel.item_id)).all()
            return {(r[0], r[1]) for r in rows}

    def pin_conversation(self, conv_id: str, label: str) -> bool:
        return self.pin_item("conversation", conv_id, label)

    def unpin_conversation(self, conv_id: str) -> bool:
        return self.unpin_item("conversation", conv_id)

    def list_pinned_conversations(self) -> list[Conversation]:
        with get_db() as session:
            stmt = (
                select(ConvModel, PinModel.pinned_at, PinModel.label)
                .join(PinModel, (PinModel.item_id == ConvModel.id) & (PinModel.item_type == "conversation"))
                .order_by(PinModel.pinned_at)
            )
            rows = session.execute(stmt).all()
            return [
                Conversation(
                    id=c.id,
                    user_id=c.user_id,
                    title=c.title,
                    pinned_at=datetime.fromisoformat(p_at) if p_at else None,
                    pinned_label=p_label,
                    created_at=datetime.fromisoformat(c.created_at),
                    updated_at=datetime.fromisoformat(c.updated_at),
                )
                for c, p_at, p_label in rows
            ]

    def get_active_knowledge_conversation(
        self, file_path: str, user_id: Optional[str] = None
    ) -> Optional[Conversation]:
        with get_db() as session:
            stmt = (
                select(ConvModel)
                .where(
                    ConvModel.conv_type == "knowledge",
                    ConvModel.file_path == file_path,
                    ConvModel.status == "active",
                )
                .order_by(ConvModel.updated_at.desc())
                .limit(1)
            )
            if user_id:
                stmt = stmt.where(ConvModel.user_id == user_id)

            c = session.scalars(stmt).first()
            if not c:
                return None

            return Conversation(
                id=c.id,
                user_id=c.user_id,
                title=c.title,
                session_id=c.session_id,
                conv_type=c.conv_type,
                file_path=c.file_path,
                status=c.status,
                messages=[],
                created_at=datetime.fromisoformat(c.created_at),
                updated_at=datetime.fromisoformat(c.updated_at),
            )

    def list_active_knowledge_conversations(self) -> list[Conversation]:
        with get_db() as session:
            models = session.scalars(
                select(ConvModel)
                .where(ConvModel.conv_type == "knowledge", ConvModel.status == "active")
                .order_by(ConvModel.updated_at.desc())
            ).all()

            return [
                Conversation(
                    id=c.id,
                    user_id=c.user_id,
                    title=c.title,
                    session_id=c.session_id,
                    conv_type=c.conv_type,
                    file_path=c.file_path,
                    status=c.status,
                    messages=[],
                    created_at=datetime.fromisoformat(c.created_at),
                    updated_at=datetime.fromisoformat(c.updated_at),
                )
                for c in models
            ]

    def get_running_conversation_ids(self) -> list[str]:
        with get_db() as session:
            return list(session.scalars(select(ConvModel.id).where(ConvModel.needs_response == 1)).all())

    def clear_all_needs_response(self) -> list[str]:
        """Clear needs_response for all conversations. Used on PM startup to unstick zombies."""
        with get_db() as session:
            models = session.scalars(select(ConvModel).where(ConvModel.needs_response == 1)).all()
            ids = [c.id for c in models]
            for c in models:
                c.needs_response = 0
            return ids

    def update_conversation(self, conv_id: str, **kwargs) -> bool:
        allowed = {"title", "session_id", "user_id", "status", "pr_url", "needs_response"}
        updates = {k: v for k, v in kwargs.items() if k in allowed}
        if not updates:
            return False

        with get_db() as session:
            c = session.get(ConvModel, conv_id)
            if not c:
                return False
            for k, v in updates.items():
                if k == "needs_response":
                    v = int(v)
                setattr(c, k, v)
            c.updated_at = datetime.now().isoformat()
            return True

    def update_conversation_usage(
        self,
        conv_id: str,
        input_tokens: int = 0,
        output_tokens: int = 0,
        cache_creation_tokens: int = 0,
        cache_read_tokens: int = 0,
        backend: Optional[str] = None,
        extra: Optional[dict] = None,
    ) -> bool:
        extra_json = json.dumps(extra) if extra else None
        with get_db() as session:
            c = session.get(ConvModel, conv_id)
            if not c:
                return False
            c.usage_input_tokens = input_tokens
            c.usage_output_tokens = output_tokens
            c.usage_cache_creation_tokens = cache_creation_tokens
            c.usage_cache_read_tokens = cache_read_tokens
            if backend is not None:
                c.usage_backend = backend
            c.usage_extra = extra_json
            c.updated_at = datetime.now().isoformat()
            return True

    def accumulate_usage(
        self,
        conv_id: str,
        input_tokens: int = 0,
        output_tokens: int = 0,
        cache_creation_tokens: int = 0,
        cache_read_tokens: int = 0,
        backend: Optional[str] = None,
        extra: Optional[dict] = None,
    ) -> bool:
        """Add usage to existing counts (for incremental updates)."""
        extra_json = json.dumps(extra) if extra else None
        with get_db() as session:
            c = session.get(ConvModel, conv_id)
            if not c:
                return False
            c.usage_input_tokens = (c.usage_input_tokens or 0) + input_tokens
            c.usage_output_tokens = (c.usage_output_tokens or 0) + output_tokens
            c.usage_cache_creation_tokens = (c.usage_cache_creation_tokens or 0) + cache_creation_tokens
            c.usage_cache_read_tokens = (c.usage_cache_read_tokens or 0) + cache_read_tokens
            if backend is not None:
                c.usage_backend = backend
            if extra_json is not None:
                c.usage_extra = extra_json
            c.updated_at = datetime.now().isoformat()
            return True

    def delete_conversation(self, conv_id: str) -> bool:
        with get_db() as session:
            c = session.get(ConvModel, conv_id)
            if not c:
                return False
            reports = session.scalars(select(ReportModel).where(ReportModel.conversation_id == conv_id)).all()
            for r in reports:
                session.delete(r)
            session.delete(c)
            return True

    def add_message(
        self,
        conv_id: str,
        type: str,
        content: str,
    ) -> Optional[Message]:
        """Add a message to a conversation. Returns the message with ID."""
        msg = Message(
            conversation_id=conv_id,
            type=type,
            content=content,
        )

        with get_db() as session:
            c = session.get(ConvModel, conv_id)
            if not c:
                return None

            model = MsgModel(
                conversation_id=conv_id,
                type=type,
                role=type,
                content=content,
                timestamp=msg.created_at.isoformat(),
            )
            session.add(model)
            session.flush()
            msg.id = model.id

            now = datetime.now().isoformat()
            if c.title is None and type == "user":
                c.title = content[:80] + ("..." if len(content) > 80 else "")
            c.updated_at = now

        return msg

    def update_message(self, message_id: int, content: str) -> bool:
        with get_db() as session:
            m = session.get(MsgModel, message_id)
            if not m:
                return False
            m.content = content
            return True

    def get_messages(
        self,
        conv_id: str,
        types: Optional[list[str]] = None,
        limit: Optional[int] = None,
    ) -> list[Message]:
        with get_db() as session:
            stmt = select(MsgModel).where(MsgModel.conversation_id == conv_id)

            if types:
                stmt = stmt.where(func.coalesce(MsgModel.type, MsgModel.role).in_(types))

            stmt = stmt.order_by(MsgModel.timestamp)

            if limit:
                stmt = stmt.limit(limit)

            models = session.scalars(stmt).all()
            return [_model_to_message(m) for m in models]

    def create_report(
        self,
        title: str,
        content: str,
        website: Optional[str] = None,
        category: Optional[str] = None,
        tags: Optional[list[str]] = None,
        original_query: Optional[str] = None,
        source_conversation_id: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> Optional[Report]:
        report = Report(
            title=title,
            content=content,
            website=website,
            category=category,
            tags=tags or [],
            original_query=original_query,
            source_conversation_id=source_conversation_id,
            user_id=user_id,
        )

        with get_db() as session:
            model = ReportModel(
                title=title,
                content=content,
                website=website,
                category=category,
                tags=json.dumps(tags) if tags else None,
                original_query=original_query,
                source_conversation_id=source_conversation_id,
                user_id=user_id,
                version=1,
                created_at=report.created_at.isoformat(),
                updated_at=report.updated_at.isoformat(),
            )
            session.add(model)
            session.flush()
            report.id = model.id

        return report

    def get_report(self, report_id: int) -> Optional[Report]:
        with get_db() as session:
            r = session.get(ReportModel, report_id)
            if not r:
                return None

            content = r.content
            if not content and r.message_id:
                msg = session.get(MsgModel, r.message_id)
                content = msg.content if msg else None

            result = _model_to_report(r)
            result.content = content
            return result

    def list_reports(
        self,
        website: Optional[str] = None,
        category: Optional[str] = None,
        include_archived: bool = False,
        limit: int = 50,
    ) -> list[Report]:
        with get_db() as session:
            stmt = select(ReportModel)

            if not include_archived:
                stmt = stmt.where((ReportModel.archived == 0) | (ReportModel.archived.is_(None)))

            if website:
                stmt = stmt.where(ReportModel.website == website)

            if category:
                stmt = stmt.where(ReportModel.category == category)

            stmt = stmt.order_by(ReportModel.updated_at.desc()).limit(limit)
            models = session.scalars(stmt).all()
            return [_model_to_report(r) for r in models]

    def archive_report(self, report_id: int) -> bool:
        with get_db() as session:
            r = session.get(ReportModel, report_id)
            if not r:
                return False
            r.archived = 1
            r.updated_at = datetime.now().isoformat()
            return True

    def update_report(self, report_id: int, **kwargs) -> bool:
        allowed = {"title", "content", "website", "category", "tags", "original_query"}
        updates = {k: v for k, v in kwargs.items() if k in allowed}
        if not updates:
            return False

        if "tags" in updates:
            updates["tags"] = json.dumps(updates["tags"])

        with get_db() as session:
            r = session.get(ReportModel, report_id)
            if not r:
                return False
            for k, v in updates.items():
                setattr(r, k, v)
            r.version = r.version + 1
            r.updated_at = datetime.now().isoformat()
            return True

    def delete_report(self, report_id: int) -> bool:
        with get_db() as session:
            r = session.get(ReportModel, report_id)
            if not r:
                return False
            session.delete(r)
            return True

    def get_all_tags(self, tag_type: Optional[str] = None) -> list[Tag]:
        with get_db() as session:
            stmt = select(TagModel)
            if tag_type:
                stmt = stmt.where(TagModel.type == tag_type).order_by(TagModel.label)
            else:
                stmt = stmt.order_by(TagModel.type, TagModel.label)
            models = session.scalars(stmt).all()
            return [_model_to_tag(t) for t in models]

    def get_tags_by_type(self) -> dict[str, list[Tag]]:
        tags = self.get_all_tags()
        result: dict[str, list[Tag]] = {}
        for tag in tags:
            if tag.type not in result:
                result[tag.type] = []
            result[tag.type].append(tag)
        return result

    def get_used_conversation_tags_by_type(
        self, active_tag_names: Optional[list[str]] = None, user_id: Optional[str] = None
    ) -> dict[str, list[Tag]]:
        """Get tags actually used by conversations, grouped by type with counts."""
        with get_db() as session:
            params: dict = {}
            conv_filter = "(c.conv_type = 'exploration' OR c.conv_type IS NULL)"

            if user_id:
                conv_filter += " AND c.user_id = :user_id"
                params["user_id"] = user_id

            if active_tag_names:
                tag_placeholders = ", ".join(f":tn{i}" for i in range(len(active_tag_names)))
                for i, name in enumerate(active_tag_names):
                    params[f"tn{i}"] = name
                params["tag_count"] = len(active_tag_names)
                conv_filter += f"""
                    AND c.id IN (
                        SELECT conversation_id FROM conversation_tags ct2
                        JOIN tags t2 ON ct2.tag_id = t2.id
                        WHERE t2.name IN ({tag_placeholders})
                        GROUP BY conversation_id
                        HAVING COUNT(DISTINCT t2.name) = :tag_count
                    )
                """

            query = text(f"""
                SELECT t.*,
                       COUNT(DISTINCT CASE
                           WHEN c.id IS NOT NULL AND {conv_filter} THEN c.id
                           ELSE NULL
                       END) as count
                FROM tags t
                INNER JOIN conversation_tags ct ON t.id = ct.tag_id
                INNER JOIN conversations c ON ct.conversation_id = c.id
                WHERE (c.conv_type = 'exploration' OR c.conv_type IS NULL)
                GROUP BY t.id, t.name, t.type, t.label
                HAVING COUNT(DISTINCT c.id) > 0
                ORDER BY t.type, t.label
            """)

            rows = session.execute(query, params).mappings().all()
            result: dict[str, list[Tag]] = {}
            for row in rows:
                tag = Tag(id=row["id"], name=row["name"], type=row["type"], label=row["label"], count=row["count"])
                if tag.type not in result:
                    result[tag.type] = []
                result[tag.type].append(tag)
            return result

    def get_used_report_tags_by_type(self) -> dict[str, list[Tag]]:
        with get_db() as session:
            stmt = (
                select(TagModel)
                .join(ReportTagModel, TagModel.id == ReportTagModel.tag_id)
                .join(ReportModel, ReportTagModel.report_id == ReportModel.id)
                .where((ReportModel.archived == 0) | (ReportModel.archived.is_(None)))
                .distinct()
                .order_by(TagModel.type, TagModel.label)
            )
            models = session.scalars(stmt).all()
            result: dict[str, list[Tag]] = {}
            for t in models:
                tag = _model_to_tag(t)
                if tag.type not in result:
                    result[tag.type] = []
                result[tag.type].append(tag)
            return result

    def get_tag_by_name(self, name: str) -> Optional[Tag]:
        with get_db() as session:
            t = session.scalars(select(TagModel).where(TagModel.name == name)).first()
            if t:
                return _model_to_tag(t)
            return None

    def set_conversation_tags(self, conv_id: str, tag_names: list[str], update_timestamp: bool = True) -> bool:
        with get_db() as session:
            existing = session.scalars(select(ConvTagModel).where(ConvTagModel.conversation_id == conv_id)).all()
            for ct in existing:
                session.delete(ct)

            for tag_name in tag_names:
                t = session.scalars(select(TagModel).where(TagModel.name == tag_name)).first()
                if t:
                    session.add(ConvTagModel(conversation_id=conv_id, tag_id=t.id))

            if update_timestamp:
                c = session.get(ConvModel, conv_id)
                if c:
                    c.updated_at = datetime.now().isoformat()
            return True

    def get_conversation_tags(self, conv_id: str) -> list[Tag]:
        with get_db() as session:
            stmt = (
                select(TagModel)
                .join(ConvTagModel, TagModel.id == ConvTagModel.tag_id)
                .where(ConvTagModel.conversation_id == conv_id)
                .order_by(TagModel.type, TagModel.label)
            )
            models = session.scalars(stmt).all()
            return [_model_to_tag(t) for t in models]

    def get_conversation_tags_batch(self, conv_ids: list[str]) -> dict[str, list[Tag]]:
        if not conv_ids:
            return {}
        with get_db() as session:
            stmt = (
                select(ConvTagModel.conversation_id, TagModel)
                .join(TagModel, ConvTagModel.tag_id == TagModel.id)
                .where(ConvTagModel.conversation_id.in_(conv_ids))
                .order_by(TagModel.type, TagModel.label)
            )
            rows = session.execute(stmt).all()
            result: dict[str, list[Tag]] = {cid: [] for cid in conv_ids}
            for conv_id, t in rows:
                result[conv_id].append(_model_to_tag(t))
            return result

    def set_report_tags(self, report_id: int, tag_names: list[str], update_timestamp: bool = True) -> bool:
        with get_db() as session:
            existing = session.scalars(select(ReportTagModel).where(ReportTagModel.report_id == report_id)).all()
            for rt in existing:
                session.delete(rt)

            for tag_name in tag_names:
                t = session.scalars(select(TagModel).where(TagModel.name == tag_name)).first()
                if t:
                    session.add(ReportTagModel(report_id=report_id, tag_id=t.id))

            if update_timestamp:
                r = session.get(ReportModel, report_id)
                if r:
                    r.updated_at = datetime.now().isoformat()
            return True

    def get_report_tags(self, report_id: int) -> list[Tag]:
        with get_db() as session:
            stmt = (
                select(TagModel)
                .join(ReportTagModel, TagModel.id == ReportTagModel.tag_id)
                .where(ReportTagModel.report_id == report_id)
                .order_by(TagModel.type, TagModel.label)
            )
            models = session.scalars(stmt).all()
            return [_model_to_tag(t) for t in models]

    def get_report_tags_batch(self, report_ids: list[int]) -> dict[int, list[Tag]]:
        if not report_ids:
            return {}
        with get_db() as session:
            stmt = (
                select(ReportTagModel.report_id, TagModel)
                .join(TagModel, ReportTagModel.tag_id == TagModel.id)
                .where(ReportTagModel.report_id.in_(report_ids))
                .order_by(TagModel.type, TagModel.label)
            )
            rows = session.execute(stmt).all()
            result: dict[int, list[Tag]] = {rid: [] for rid in report_ids}
            for report_id, t in rows:
                result[report_id].append(_model_to_tag(t))
            return result

    def list_conversations_with_tags(
        self,
        user_id: Optional[str] = None,
        tag_names: Optional[list[str]] = None,
        limit: int = 100,
    ) -> list[tuple[Conversation, list[Tag]]]:
        with get_db() as session:
            conditions = ["(c.conv_type = 'exploration' OR c.conv_type IS NULL)"]
            params: dict = {}

            if user_id:
                conditions.append("c.user_id = :user_id")
                params["user_id"] = user_id

            if tag_names:
                for i, tag_name in enumerate(tag_names):
                    key = f"tag_{i}"
                    conditions.append(f"""
                        EXISTS (
                            SELECT 1 FROM conversation_tags ct
                            JOIN tags t ON ct.tag_id = t.id
                            WHERE ct.conversation_id = c.id AND t.name = :{key}
                        )
                    """)
                    params[key] = tag_name

            where = "WHERE " + " AND ".join(conditions) if conditions else ""
            params["lim"] = limit

            query = text(f"""
                SELECT c.*, r.id as report_id, r.title as report_title
                FROM conversations c
                LEFT JOIN reports r ON r.conversation_id = c.id AND r.id IS NULL
                {where}
                ORDER BY c.updated_at DESC
                LIMIT :lim
            """)

            rows = session.execute(query, params).mappings().all()

            conv_ids = [row["id"] for row in rows]
            tags_by_conv = self._batch_fetch_conv_tags(session, conv_ids)

            return [
                (_conv_with_report_row(row, row["report_id"], row["report_title"]), tags_by_conv.get(row["id"], []))
                for row in rows
            ]

    def list_reports_with_tags(
        self,
        tag_names: Optional[list[str]] = None,
        include_archived: bool = False,
        limit: int = 100,
    ) -> list[tuple[Report, list[Tag]]]:
        with get_db() as session:
            conditions: list[str] = []
            params: dict = {}

            if not include_archived:
                conditions.append("(r.archived = 0 OR r.archived IS NULL)")

            if tag_names:
                for i, tag_name in enumerate(tag_names):
                    key = f"tag_{i}"
                    conditions.append(f"""
                        EXISTS (
                            SELECT 1 FROM report_tags rt
                            JOIN tags t ON rt.tag_id = t.id
                            WHERE rt.report_id = r.id AND t.name = :{key}
                        )
                    """)
                    params[key] = tag_name

            where = "WHERE " + " AND ".join(conditions) if conditions else ""
            params["lim"] = limit

            query = text(f"""
                SELECT r.*
                FROM reports r
                {where}
                ORDER BY r.updated_at DESC
                LIMIT :lim
            """)

            rows = session.execute(query, params).mappings().all()

            report_ids = [row["id"] for row in rows]
            tags_by_report = self._batch_fetch_report_tags(session, report_ids)

            return [(_model_to_report_from_row(row), tags_by_report.get(row["id"], [])) for row in rows]

    def add_uploaded_file(
        self,
        conversation_id: Optional[str],
        user_id: Optional[str],
        original_filename: str,
        stored_filename: str,
        storage_path: str,
        file_size: int,
        sha256_hash: str,
        mime_type: Optional[str] = None,
        is_text: bool = False,
        av_scanned: bool = False,
        av_clean: Optional[bool] = None,
    ) -> Optional[UploadedFile]:
        """Add a new uploaded file record."""
        uploaded_file = UploadedFile(
            conversation_id=conversation_id,
            user_id=user_id,
            original_filename=original_filename,
            stored_filename=stored_filename,
            storage_path=storage_path,
            file_size=file_size,
            mime_type=mime_type,
            sha256_hash=sha256_hash,
            is_text=is_text,
            av_scanned=av_scanned,
            av_clean=av_clean,
        )

        with get_db() as session:
            model = FileModel(
                conversation_id=conversation_id,
                user_id=user_id,
                original_filename=original_filename,
                stored_filename=stored_filename,
                storage_path=storage_path,
                file_size=file_size,
                mime_type=mime_type,
                sha256_hash=sha256_hash,
                is_text=is_text,
                av_scanned=av_scanned,
                av_clean=av_clean,
                created_at=uploaded_file.created_at.isoformat(),
            )
            session.add(model)
            session.flush()
            uploaded_file.id = model.id

        return uploaded_file

    def get_uploaded_file(self, file_id: int) -> Optional[UploadedFile]:
        with get_db() as session:
            f = session.get(FileModel, file_id)
            if not f:
                return None
            return _model_to_uploaded_file(f)

    def get_uploaded_file_by_hash(self, sha256_hash: str) -> Optional[UploadedFile]:
        with get_db() as session:
            f = session.scalars(select(FileModel).where(FileModel.sha256_hash == sha256_hash).limit(1)).first()
            if not f:
                return None
            return _model_to_uploaded_file(f)

    def get_conversation_files(self, conversation_id: str) -> list[UploadedFile]:
        with get_db() as session:
            models = session.scalars(
                select(FileModel).where(FileModel.conversation_id == conversation_id).order_by(FileModel.created_at)
            ).all()
            return [_model_to_uploaded_file(f) for f in models]

    def update_uploaded_file_av_status(self, file_id: int, av_scanned: bool, av_clean: Optional[bool]) -> bool:
        with get_db() as session:
            f = session.get(FileModel, file_id)
            if not f:
                return False
            f.av_scanned = av_scanned
            f.av_clean = av_clean
            return True

    def delete_uploaded_file(self, file_id: int) -> bool:
        with get_db() as session:
            f = session.get(FileModel, file_id)
            if not f:
                return False
            session.delete(f)
            return True

    def get_messages_since(self, conv_id: str, after_id: int) -> list[Message]:
        with get_db() as session:
            models = session.scalars(
                select(MsgModel)
                .where(MsgModel.conversation_id == conv_id, MsgModel.id > after_id)
                .order_by(MsgModel.id)
            ).all()
            return [_model_to_message(m) for m in models]

    def get_last_message_role(self, conversation_id: str) -> Optional[str]:
        with get_db() as session:
            m = session.scalars(
                select(MsgModel)
                .where(MsgModel.conversation_id == conversation_id)
                .order_by(MsgModel.id.desc())
                .limit(1)
            ).first()
            if not m:
                return None
            return m.type or m.role

    @staticmethod
    def _batch_fetch_conv_tags(session, conv_ids: list[str]) -> dict[str, list[Tag]]:
        result: dict[str, list[Tag]] = {cid: [] for cid in conv_ids}
        if not conv_ids:
            return result
        stmt = (
            select(ConvTagModel.conversation_id, TagModel)
            .join(TagModel, ConvTagModel.tag_id == TagModel.id)
            .where(ConvTagModel.conversation_id.in_(conv_ids))
            .order_by(TagModel.type, TagModel.label)
        )
        rows = session.execute(stmt).all()
        for conv_id, t in rows:
            result[conv_id].append(_model_to_tag(t))
        return result

    @staticmethod
    def _batch_fetch_report_tags(session, report_ids: list[int]) -> dict[int, list[Tag]]:
        result: dict[int, list[Tag]] = {rid: [] for rid in report_ids}
        if not report_ids:
            return result
        stmt = (
            select(ReportTagModel.report_id, TagModel)
            .join(TagModel, ReportTagModel.tag_id == TagModel.id)
            .where(ReportTagModel.report_id.in_(report_ids))
            .order_by(TagModel.type, TagModel.label)
        )
        rows = session.execute(stmt).all()
        for report_id, t in rows:
            result[report_id].append(_model_to_tag(t))
        return result

    def _generate_unique_slug(self) -> str:
        with get_db() as session:
            for _ in range(100):
                slug = f"{random.choice(ADJECTIVES)}-{random.choice(NOUNS)}"
                existing = session.execute(
                    select(ProjectModel).where(ProjectModel.slug == slug)
                ).scalar_one_or_none()
                if not existing:
                    return slug
            return f"project-{uuid.uuid4().hex[:8]}"

    def create_project(self, name: str, user_id: Optional[str] = None, description: Optional[str] = None) -> Project:
        project_id = str(uuid.uuid4())
        slug = self._generate_unique_slug()
        now = datetime.now()
        with get_db() as session:
            model = ProjectModel(
                id=project_id,
                user_id=user_id,
                name=name,
                slug=slug,
                description=description,
                created_at=now.isoformat(),
                updated_at=now.isoformat(),
            )
            session.add(model)
        return Project(id=project_id, user_id=user_id, name=name, slug=slug,
                       description=description, created_at=now, updated_at=now)

    def get_project(self, project_id: str) -> Optional[Project]:
        with get_db() as session:
            model = session.execute(
                select(ProjectModel).where(ProjectModel.id == project_id)
            ).scalar_one_or_none()
            return _model_to_project(model) if model else None

    def get_project_by_slug(self, slug: str) -> Optional[Project]:
        with get_db() as session:
            model = session.execute(
                select(ProjectModel).where(ProjectModel.slug == slug)
            ).scalar_one_or_none()
            return _model_to_project(model) if model else None

    def list_projects(self, user_id: Optional[str] = None, limit: int = 100) -> list[Project]:
        with get_db() as session:
            stmt = select(ProjectModel).order_by(ProjectModel.updated_at.desc()).limit(limit)
            if user_id:
                stmt = stmt.where(ProjectModel.user_id == user_id)
            models = session.scalars(stmt).all()
            return [_model_to_project(m) for m in models]

    VALID_PROJECT_COLUMNS = frozenset({
        "name", "description", "spec", "status", "workflow_phase",
    })

    def update_project(self, project_id: str, **kwargs) -> bool:
        updates = {k: v for k, v in kwargs.items() if k in self.VALID_PROJECT_COLUMNS}
        if not updates:
            return False
        updates["updated_at"] = datetime.now().isoformat()
        with get_db() as session:
            model = session.execute(
                select(ProjectModel).where(ProjectModel.id == project_id)
            ).scalar_one_or_none()
            if not model:
                return False
            for key, value in updates.items():
                setattr(model, key, value)
            return True

    def list_project_conversations(self, project_id: str) -> list[Conversation]:
        with get_db() as session:
            models = session.scalars(
                select(ConvModel)
                .where(ConvModel.project_id == project_id)
                .order_by(ConvModel.updated_at.desc())
            ).all()
            return [
                Conversation(
                    id=c.id,
                    user_id=c.user_id,
                    title=c.title,
                    conv_type=c.conv_type or "exploration",
                    status=c.status or "active",
                    project_id=c.project_id,
                    needs_response=bool(c.needs_response) if c.needs_response else False,
                    created_at=datetime.fromisoformat(c.created_at),
                    updated_at=datetime.fromisoformat(c.updated_at),
                )
                for c in models
            ]

ADJECTIVES = [
    "swift", "bright", "calm", "dark", "eager", "fair", "gentle", "happy",
    "keen", "lively", "merry", "noble", "proud", "quiet", "rare", "sharp",
    "true", "vivid", "warm", "wise",
]
NOUNS = [
    "brook", "cloud", "dawn", "elm", "fern", "grove", "hawk", "iris",
    "jade", "knoll", "lake", "moss", "oak", "pine", "reef", "sage",
    "thorn", "vale", "wave", "wren",
]


@dataclass
class Project:
    """Expert-mode project."""

    id: str = ""
    user_id: Optional[str] = None
    name: str = ""
    slug: str = ""
    description: Optional[str] = None
    spec: Optional[str] = None
    status: str = "draft"
    workflow_phase: str = "planning"
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)


def _model_to_project(p: ProjectModel) -> Project:
    return Project(
        id=p.id,
        user_id=p.user_id,
        name=p.name,
        slug=p.slug,
        description=p.description,
        spec=p.spec,
        status=p.status or "draft",
        workflow_phase=p.workflow_phase or "planning",
        created_at=datetime.fromisoformat(p.created_at),
        updated_at=datetime.fromisoformat(p.updated_at),
    )


def _model_to_report_from_row(row) -> Report:
    return Report(
        id=row["id"],
        title=row["title"],
        website=row["website"],
        category=row["category"],
        tags=json.loads(row["tags"]) if row["tags"] else [],
        original_query=row["original_query"],
        source_conversation_id=row["source_conversation_id"],
        user_id=row["user_id"],
        archived=bool(row["archived"]) if row["archived"] else False,
        version=row["version"],
        created_at=datetime.fromisoformat(row["created_at"]),
        updated_at=datetime.fromisoformat(row["updated_at"]),
        conversation_id=row["conversation_id"],
        message_id=row["message_id"],
    )


class LazyConversationStore:
    _store = None

    def __getattr__(self, name):
        if LazyConversationStore._store is None:
            LazyConversationStore._store = ConversationStore()
        return getattr(LazyConversationStore._store, name)


store = LazyConversationStore()
