"""Conversation, message, flag, and usage persistence."""

import json
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import func, or_, select

from web import session_sync
from web.db import get_db
from web.helpers import utcnow
from web.models import Conversation as ConvModel
from web.models import Message as MsgModel
from web.models import PinnedItem as PinModel
from web.models import Report as ReportModel
from web.models import UsageEvent as UsageEventModel
from web.stores.records import (
    Conversation,
    Message,
    conv_with_report_row,
    model_to_message,
    model_to_report,
)


class ConversationsMixin:
    def create_conversation(
        self,
        user_id: Optional[str] = None,
        conv_type: str = "exploration",
        file_path: Optional[str] = None,
    ) -> Conversation:
        conv = Conversation(
            id=str(uuid.uuid4()),
            user_id=user_id,
            conv_type=conv_type,
            file_path=file_path,
        )

        with get_db() as session:
            model = ConvModel(
                id=conv.id,
                user_id=conv.user_id,
                title=conv.title,
                session_id=conv.session_id,
                conv_type=conv.conv_type,
                file_path=conv.file_path,
                status=conv.status,
                created_at=conv.created_at,
                updated_at=conv.updated_at,
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
                messages = [model_to_message(m) for m in msg_models]

            report_model = session.scalars(select(ReportModel).where(ReportModel.conversation_id == conv_id)).first()

            report = None
            if report_model:
                report = model_to_report(report_model)

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
                messages=messages,
                report=report,
                usage_input_tokens=c.usage_input_tokens or 0,
                usage_output_tokens=c.usage_output_tokens or 0,
                usage_cache_creation_tokens=c.usage_cache_creation_tokens or 0,
                usage_cache_read_tokens=c.usage_cache_read_tokens or 0,
                usage_backend=c.usage_backend,
                usage_extra=usage_extra,
                pinned_at=p_pinned_at,
                pinned_label=p_label,
                flagged_at=c.flagged_at,
                flag_reason=c.flag_reason,
                flag_user_id=c.flag_user_id,
                needs_response=bool(c.needs_response) if c.needs_response else False,
                created_at=c.created_at,
                updated_at=c.updated_at,
            )

    def fork_conversation(self, source_conv_id: str, new_user_id: str) -> Optional[Conversation]:
        """Deep copy a conversation for a new user."""
        source = self.get_conversation(source_conv_id, include_messages=True)
        if not source:
            return None

        now = utcnow()
        new_id = str(uuid.uuid4())

        new_session_id = None
        if source.session_id:
            candidate = str(uuid.uuid4())
            if session_sync.copy_session(source.session_id, candidate):
                new_session_id = candidate

        with get_db() as session:
            model = ConvModel(
                id=new_id,
                user_id=new_user_id,
                title=source.title,
                session_id=new_session_id,
                conv_type=source.conv_type,
                file_path=source.file_path,
                status="active",
                forked_from=source_conv_id,
                created_at=now,
                updated_at=now,
            )
            session.add(model)

            for msg in source.messages:
                session.add(
                    MsgModel(
                        conversation_id=new_id,
                        type=msg.type,
                        role=msg.type,
                        content=msg.content,
                        timestamp=msg.created_at,
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
            stmt = select(ConvModel, ReportModel.id, ReportModel.title).outerjoin(
                ReportModel, ReportModel.conversation_id == ConvModel.id
            )

            if user_id:
                stmt = stmt.where(ConvModel.user_id == user_id)

            if conv_type:
                stmt = stmt.where(ConvModel.conv_type == conv_type)
            else:
                stmt = stmt.where(or_(ConvModel.conv_type == "exploration", ConvModel.conv_type.is_(None)))

            if exclude_report_containers:
                stmt = stmt.where(ReportModel.id.is_(None))

            stmt = stmt.order_by(ConvModel.updated_at.desc()).limit(limit)
            rows = session.execute(stmt).all()
            return [conv_with_report_row(conv, report_id, report_title) for conv, report_id, report_title in rows]

    def flag_conversation(self, conv_id: str, user_id: str, reason: str) -> bool:
        with get_db() as session:
            c = session.get(ConvModel, conv_id)
            if not c:
                return False
            c.flagged_at = utcnow()
            c.flag_reason = reason
            c.flag_user_id = user_id
            return True

    def unflag_conversation(self, conv_id: str) -> bool:
        with get_db() as session:
            c = session.get(ConvModel, conv_id)
            if not c:
                return False
            c.flagged_at = None
            c.flag_reason = None
            c.flag_user_id = None
            return True

    def list_flagged_conversations(self) -> list[Conversation]:
        with get_db() as session:
            stmt = select(ConvModel).where(ConvModel.flagged_at.is_not(None)).order_by(ConvModel.flagged_at.desc())
            rows = session.scalars(stmt).all()
            return [
                Conversation(
                    id=c.id,
                    user_id=c.user_id,
                    title=c.title,
                    flagged_at=c.flagged_at,
                    flag_reason=c.flag_reason,
                    flag_user_id=c.flag_user_id,
                    created_at=c.created_at,
                    updated_at=c.updated_at,
                )
                for c in rows
            ]

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
                    pinned_at=p_at,
                    pinned_label=p_label,
                    created_at=c.created_at,
                    updated_at=c.updated_at,
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
                created_at=c.created_at,
                updated_at=c.updated_at,
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
                    created_at=c.created_at,
                    updated_at=c.updated_at,
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
            c.updated_at = utcnow()
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
            c.updated_at = utcnow()
            return True

    def insert_usage_event(
        self,
        conversation_id: str,
        cli_message_id: Optional[str],
        timestamp: datetime,
        model: Optional[str],
        backend: str,
        usage: dict,
        kind: str = "turn",
    ) -> None:
        cache_creation = usage.get("cache_creation") or {}
        cc_5m = cache_creation.get("ephemeral_5m_input_tokens")
        cc_1h = cache_creation.get("ephemeral_1h_input_tokens")
        if cc_5m is None and cc_1h is None:
            cc_5m = usage.get("cache_creation_input_tokens", 0) or 0
            cc_1h = 0
        else:
            cc_5m = cc_5m or 0
            cc_1h = cc_1h or 0
        server_tool_use = usage.get("server_tool_use") or {}
        input_tokens = usage.get("input_tokens", 0) or 0
        output_tokens = usage.get("output_tokens", 0) or 0
        cache_read = usage.get("cache_read_input_tokens", 0) or 0
        with get_db() as session:
            session.add(
                UsageEventModel(
                    conversation_id=conversation_id,
                    cli_message_id=cli_message_id,
                    timestamp=timestamp,
                    kind=kind,
                    model=model,
                    backend=backend,
                    service_tier=usage.get("service_tier"),
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    cache_creation_5m_tokens=cc_5m,
                    cache_creation_1h_tokens=cc_1h,
                    cache_read_tokens=cache_read,
                    web_search_requests=server_tool_use.get("web_search_requests", 0) or 0,
                    web_fetch_requests=server_tool_use.get("web_fetch_requests", 0) or 0,
                    raw=usage,
                )
            )
            c = session.get(ConvModel, conversation_id)
            if c is not None:
                c.usage_input_tokens = (c.usage_input_tokens or 0) + input_tokens
                c.usage_output_tokens = (c.usage_output_tokens or 0) + output_tokens
                c.usage_cache_creation_tokens = (c.usage_cache_creation_tokens or 0) + cc_5m + cc_1h
                c.usage_cache_read_tokens = (c.usage_cache_read_tokens or 0) + cache_read
                c.usage_backend = backend
                if usage.get("service_tier"):
                    c.usage_extra = json.dumps({"service_tier": usage["service_tier"]})
                c.updated_at = utcnow()

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
                timestamp=msg.created_at,
            )
            session.add(model)
            session.flush()
            msg.id = model.id

            now = utcnow()
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
            return [model_to_message(m) for m in models]

    def get_messages_since(self, conv_id: str, after_id: int) -> list[Message]:
        with get_db() as session:
            models = session.scalars(
                select(MsgModel)
                .where(MsgModel.conversation_id == conv_id, MsgModel.id > after_id)
                .order_by(MsgModel.id)
            ).all()
            return [model_to_message(m) for m in models]

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
