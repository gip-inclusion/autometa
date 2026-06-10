"""Tag queries for conversations and reports."""

from typing import Optional

from sqlalchemy import and_, case, distinct, func, or_, select

from web.db import get_db
from web.helpers import utcnow
from web.models import Conversation as ConvModel
from web.models import ConversationTag as ConvTagModel
from web.models import Report as ReportModel
from web.models import ReportTag as ReportTagModel
from web.models import Tag as TagModel
from web.stores.records import Conversation, Report, Tag, conv_with_report_row, model_to_report, model_to_tag


class TagsMixin:
    def get_all_tags(self, tag_type: Optional[str] = None) -> list[Tag]:
        with get_db() as session:
            stmt = select(TagModel)
            if tag_type:
                stmt = stmt.where(TagModel.type == tag_type).order_by(TagModel.label)
            else:
                stmt = stmt.order_by(TagModel.type, TagModel.label)
            models = session.scalars(stmt).all()
            return [model_to_tag(t) for t in models]

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
            conv_match = [or_(ConvModel.conv_type == "exploration", ConvModel.conv_type.is_(None))]

            if user_id:
                conv_match.append(ConvModel.user_id == user_id)

            if active_tag_names:
                matching_convs = (
                    select(ConvTagModel.conversation_id)
                    .join(TagModel, ConvTagModel.tag_id == TagModel.id)
                    .where(TagModel.name.in_(active_tag_names))
                    .group_by(ConvTagModel.conversation_id)
                    .having(func.count(distinct(TagModel.name)) == len(active_tag_names))
                )
                conv_match.append(ConvModel.id.in_(matching_convs))

            count_expr = func.count(distinct(case((and_(*conv_match), ConvModel.id))))
            stmt = (
                select(TagModel, count_expr)
                .join(ConvTagModel, TagModel.id == ConvTagModel.tag_id)
                .join(ConvModel, ConvTagModel.conversation_id == ConvModel.id)
                .where(or_(ConvModel.conv_type == "exploration", ConvModel.conv_type.is_(None)))
                .group_by(TagModel.id, TagModel.name, TagModel.type, TagModel.label)
                .having(func.count(distinct(ConvModel.id)) > 0)
                .order_by(TagModel.type, TagModel.label)
            )

            result: dict[str, list[Tag]] = {}
            for t, count in session.execute(stmt).all():
                result.setdefault(t.type, []).append(model_to_tag(t, count))
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
                tag = model_to_tag(t)
                if tag.type not in result:
                    result[tag.type] = []
                result[tag.type].append(tag)
            return result

    def get_tag_by_name(self, name: str) -> Optional[Tag]:
        with get_db() as session:
            t = session.scalars(select(TagModel).where(TagModel.name == name)).first()
            if t:
                return model_to_tag(t)
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
                    c.updated_at = utcnow()
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
            return [model_to_tag(t) for t in models]

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
                result[conv_id].append(model_to_tag(t))
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
                    r.updated_at = utcnow()
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
            return [model_to_tag(t) for t in models]

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
                result[report_id].append(model_to_tag(t))
            return result

    def list_conversations_with_tags(
        self,
        user_id: Optional[str] = None,
        tag_names: Optional[list[str]] = None,
        limit: int = 100,
    ) -> list[tuple[Conversation, list[Tag]]]:
        with get_db() as session:
            stmt = select(ConvModel).where(or_(ConvModel.conv_type == "exploration", ConvModel.conv_type.is_(None)))

            if user_id:
                stmt = stmt.where(ConvModel.user_id == user_id)

            if tag_names:
                for tag_name in tag_names:
                    stmt = stmt.where(
                        select(ConvTagModel.conversation_id)
                        .join(TagModel, ConvTagModel.tag_id == TagModel.id)
                        .where(ConvTagModel.conversation_id == ConvModel.id, TagModel.name == tag_name)
                        .exists()
                    )

            stmt = stmt.order_by(ConvModel.updated_at.desc()).limit(limit)
            convs = session.scalars(stmt).all()

            tags_by_conv = self._batch_fetch_conv_tags(session, [c.id for c in convs])

            # Why: the legacy SQL joined reports with `AND r.id IS NULL`, which never matches — kept as no report.
            return [(conv_with_report_row(c, None, None), tags_by_conv.get(c.id, [])) for c in convs]

    def list_reports_with_tags(
        self,
        tag_names: Optional[list[str]] = None,
        include_archived: bool = False,
        limit: int = 100,
    ) -> list[tuple[Report, list[Tag]]]:
        with get_db() as session:
            stmt = select(ReportModel)

            if not include_archived:
                stmt = stmt.where(or_(ReportModel.archived == 0, ReportModel.archived.is_(None)))

            if tag_names:
                for tag_name in tag_names:
                    stmt = stmt.where(
                        select(ReportTagModel.report_id)
                        .join(TagModel, ReportTagModel.tag_id == TagModel.id)
                        .where(ReportTagModel.report_id == ReportModel.id, TagModel.name == tag_name)
                        .exists()
                    )

            stmt = stmt.order_by(ReportModel.updated_at.desc()).limit(limit)
            reports = session.scalars(stmt).all()

            tags_by_report = self._batch_fetch_report_tags(session, [r.id for r in reports])

            return [(model_to_report(r), tags_by_report.get(r.id, [])) for r in reports]

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
            result[conv_id].append(model_to_tag(t))
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
            result[report_id].append(model_to_tag(t))
        return result
