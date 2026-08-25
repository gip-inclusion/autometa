"""Per-user favorites (conversations, reports, apps)."""

from sqlalchemy import func, select

from web.db import get_db
from web.helpers import utcnow
from web.models import UserFavorite as FavoriteModel
from web.stores.records import Favorite


class FavoritesMixin:
    def add_favorite(self, user_id: str, item_type: str, item_id: str) -> bool:
        with get_db() as session:
            existing = session.scalars(
                select(FavoriteModel).where(
                    FavoriteModel.user_id == user_id,
                    FavoriteModel.item_type == item_type,
                    FavoriteModel.item_id == str(item_id),
                )
            ).first()
            if existing:
                return True
            last = session.scalar(select(func.max(FavoriteModel.position)).where(FavoriteModel.user_id == user_id))
            session.add(
                FavoriteModel(
                    user_id=user_id,
                    item_type=item_type,
                    item_id=str(item_id),
                    position=0 if last is None else last + 1,
                    created_at=utcnow(),
                )
            )
            return True

    def remove_favorite(self, user_id: str, item_type: str, item_id: str) -> bool:
        with get_db() as session:
            existing = session.scalars(
                select(FavoriteModel).where(
                    FavoriteModel.user_id == user_id,
                    FavoriteModel.item_type == item_type,
                    FavoriteModel.item_id == str(item_id),
                )
            ).first()
            if not existing:
                return False
            session.delete(existing)
            return True

    def list_favorites(self, user_id: str) -> list[Favorite]:
        with get_db() as session:
            models = session.scalars(
                select(FavoriteModel)
                .where(FavoriteModel.user_id == user_id)
                .order_by(FavoriteModel.position, FavoriteModel.id)
            ).all()
            return [
                Favorite(
                    id=m.id,
                    user_id=m.user_id,
                    item_type=m.item_type,
                    item_id=m.item_id,
                    position=m.position,
                    created_at=m.created_at,
                )
                for m in models
            ]

    def get_favorite_ids(self, user_id: str) -> set[tuple[str, str]]:
        with get_db() as session:
            rows = session.execute(
                select(FavoriteModel.item_type, FavoriteModel.item_id).where(FavoriteModel.user_id == user_id)
            ).all()
            return {(r[0], r[1]) for r in rows}

    def reorder_favorites(self, user_id: str, items: list[tuple[str, str]]) -> bool:
        with get_db() as session:
            rows = {
                (m.item_type, m.item_id): m
                for m in session.scalars(select(FavoriteModel).where(FavoriteModel.user_id == user_id))
            }
            keys = [(str(item_type), str(item_id)) for item_type, item_id in items]
            ordered = [rows.pop(key) for key in keys if key in rows]
            remaining = sorted(rows.values(), key=lambda m: m.position)
            for position, model in enumerate(ordered + remaining):
                model.position = position
            return True
