"""Pinned items (conversations, reports, apps)."""

from typing import Optional

from sqlalchemy import select

from web.db import get_db
from web.helpers import utcnow
from web.models import PinnedItem as PinModel
from web.stores.records import PinnedItem


class PinsMixin:
    def pin_item(self, item_type: str, item_id: str, label: str) -> bool:
        with get_db() as session:
            now = utcnow()
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
                    pinned_at=m.pinned_at,
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
