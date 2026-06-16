"""Report persistence."""

import json
from typing import Optional

from sqlalchemy import select

from web.db import get_db
from web.helpers import utcnow
from web.models import Message as MsgModel
from web.models import Report as ReportModel
from web.stores.records import Report, model_to_report


class ReportsMixin:
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
                created_at=report.created_at,
                updated_at=report.updated_at,
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

            result = model_to_report(r)
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
            return [model_to_report(r) for r in models]

    def archive_report(self, report_id: int) -> bool:
        with get_db() as session:
            r = session.get(ReportModel, report_id)
            if not r:
                return False
            r.archived = 1
            r.updated_at = utcnow()
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
            r.updated_at = utcnow()
            return True

    def delete_report(self, report_id: int) -> bool:
        with get_db() as session:
            r = session.get(ReportModel, report_id)
            if not r:
                return False
            session.delete(r)
            return True
